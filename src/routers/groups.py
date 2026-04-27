from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Query, Form, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import ValidationError

from src.core.dependencies import get_current_user
from src.core.exceptions import AppError
from src.core.config import settings

import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository
import src.repositories.user_repository as user_repository

from src.schemas.group import CreateGroupRequest, GroupResponse, MemberResponse, MemberWithBalanceResponse, TransferRoleRequest, UpdateM2Request, JoinGroupRequest
from src.schemas.expense import CreateExpenseRequest, ExpenseResponse, MonthlySummaryResponse

import src.services.group_service as group_service
import src.services.expense_service as expense_service
import src.services.receipt_service as receipt_service

router = APIRouter(prefix="/groups", tags=["groups"])

def _handle(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AppError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("", status_code=201, response_model=GroupResponse)
def create_group(body: CreateGroupRequest, user=Depends(get_current_user)):
    user_id = int(user["sub"])
    group = _handle(group_service.create_group, user_id, body)

    admin_user = user_repository.find_by_id(user_id)
    admin_name = admin_user.full_name if admin_user else "Administrador"
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        icon=group.icon,
        member_count=1,
        your_role="Administrador",
        invite_code=group.invite_code,
        admin_name=admin_name
    )

@router.get("", response_model=list[GroupResponse])
def list_groups(user=Depends(get_current_user)):
    user_id = int(user["sub"])
    groups = group_repository.find_all_groups()
    result = []
    for g in groups:
        member = group_repository.get_member(g.id, user_id)
        result.append(
            GroupResponse(
                id=g.id,
                name=g.name,
                description=g.description,
                icon=g.icon,
                member_count=g.member_count,
                admin_name=g.admin_name,
                your_role=member.role if member else None,
            )
        )
    return result

@router.get("/mine", response_model=GroupResponse)
def get_my_group(user=Depends(get_current_user)):
    user_id = int(user["sub"])
    group = group_repository.get_user_group(user_id)
    if not group:
        raise HTTPException(status_code=404, detail="Sin grupo")
    member = group_repository.get_member(group.id, user_id)
    members = group_repository.get_members(group.id)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        icon=group.icon,
        member_count=len(members),
        your_role=member.role if member else None,
        invite_code=group.invite_code,
    )

@router.post("/join", status_code=200, summary="Unirse a un consorcio con código")
def join_group(body: JoinGroupRequest, user=Depends(get_current_user)):
    user_id = int(user["sub"])
    group_name = _handle(group_service.join_group, user_id, body)
    return {"message": f"Te has unido a {group_name} exitosamente"}

@router.get("/{group_id}/members/balances", response_model=list[MemberWithBalanceResponse])
def get_members_balances(group_id: int, user=Depends(get_current_user)):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return group_repository.get_members_with_balance(group_id)


@router.get("/{group_id}/members", response_model=list[MemberResponse])
def get_members(group_id: int, user=Depends(get_current_user)):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return group_repository.get_members(group_id)

@router.patch("/{group_id}/transfer-admin", status_code=200)
def transfer_admin(group_id: int, body: TransferRoleRequest, user=Depends(get_current_user)):
    user_id = int(user["sub"])
    _handle(group_service.transfer_admin, group_id, user_id, body.newAdminUserId)
    return {"message": "Rol de Administrador transferido correctamente"}

@router.post("/{group_id}/leave", status_code=200)
def leave_group(group_id: int, user=Depends(get_current_user)):
    user_id = int(user["sub"])
    _handle(group_service.leave_group, group_id, user_id)
    return {"message": "Saliste del grupo correctamente"}

@router.post("/{group_id}/expenses", status_code=201, response_model=ExpenseResponse)
async def create_expense(
    group_id: int,
    expense_data: str = Form(..., description="JSON string del CreateExpenseRequest"),
    receipt: Optional[UploadFile] = File(default=None),
    user=Depends(get_current_user),
):
    user_id = int(user["sub"])
    
    # 1. Convertimos el string JSON a nuestro modelo complejo V2
    try:
        import json
        body_dict = json.loads(expense_data)
        # Aquí es donde falla si los nombres son distintos
        body = CreateExpenseRequest(**body_dict)
    except Exception as e:
        # Esto te va a imprimir en la pantalla de la app qué campo falta
        raise HTTPException(status_code=422, detail=f"Error de validación: {str(e)}")

    # 2. Guardamos la foto de Thiago (si existe)
    receipt_url = None
    if receipt and receipt.filename:
        receipt_url = await receipt_service.save_receipt(receipt)

    # 3. Mandamos TODO a nuestro motor de gastos
    expense = _handle(expense_service.create_expense, group_id, user_id, body, receipt_url)

    paid_by_user_id = None
    paid_by_name = "Varios pagadores"

    if len(body.payments) == 1:
        paid_by_user_id = body.payments[0].user_id
        payer = user_repository.find_by_id(paid_by_user_id)
        paid_by_name = payer.full_name if payer else "Administrador"

    return ExpenseResponse(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        category=expense.category,
        paid_by_user_id=paid_by_user_id,
        paid_by_name=paid_by_name,
        created_at=expense.created_at,
        receipt_url=receipt_url
    )

@router.get("/{group_id}/expenses", response_model=list[ExpenseResponse])
def list_expenses(
    group_id: int,
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
    user=Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month
    expenses = expense_repository.list_expenses(group_id, year, month)
    return [
        ExpenseResponse(
            id=e.id,
            description=e.description,
            amount=e.amount,
            category=e.category,
            paid_by_name=e.paid_by_name,
            paid_by_user_id=e.paid_by_user_id,
            created_at=e.created_at,
            receipt_url=e.receipt_url,
        )
        for e in expenses
    ]

@router.get("/{group_id}/expenses/{expense_id}/receipt")
def get_expense_receipt(
    group_id: int,
    expense_id: int,
    user=Depends(get_current_user),
):
    with __import__("src.database.db", fromlist=["get_db_cursor"]).get_db_cursor() as cur:
        cur.execute(
            "SELECT receipt_url FROM expenses WHERE id = %s AND group_id = %s",
            (expense_id, group_id),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Gasto no encontrado")

    receipt_url = row["receipt_url"]
    if not receipt_url:
        raise HTTPException(status_code=404, detail="Este gasto no tiene comprobante")

    relative = receipt_url.lstrip("/")
    parts = relative.split("/", 1)
    file_path = os.path.join(settings.uploads_dir, parts[1] if len(parts) > 1 else parts[0])

    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Archivo de comprobante no encontrado")

    return FileResponse(file_path)

@router.get("/{group_id}/summary", response_model=MonthlySummaryResponse)
def get_summary(
    group_id: int,
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
    user=Depends(get_current_user),
):
    user_id = int(user["sub"])
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month
    return expense_repository.get_monthly_summary(group_id, user_id, year, month)

@router.put("/{group_id}/m2", summary="Actualizar metros cuadrados de las unidades")
def update_group_m2(
    group_id: int, 
    data: UpdateM2Request,
    current_user_id: int 
):
    member = group_repository.get_member(group_id, current_user_id)
    if not member or member.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Acceso denegado: Solo el administrador puede modificar los metros cuadrados")

    m2_data = [{"user_id": m.user_id, "m2": m.m2} for m in data.members]
    group_repository.update_m2(group_id, m2_data)
    
    return {"message": "Metros cuadrados actualizados correctamente"}