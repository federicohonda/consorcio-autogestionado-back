from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.dependencies import get_current_user
from src.core.exceptions import AppError
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository
from src.schemas.group import CreateGroupRequest, GroupResponse, MemberResponse, TransferRoleRequest
from src.schemas.expense import CreateExpenseRequest, ExpenseResponse, MonthlySummaryResponse
import src.services.group_service as group_service
import src.services.expense_service as expense_service
from src.schemas.group import UpdateM2Request, JoinGroupRequest
from src.repositories.user_repository import find_by_id
from src.repositories import user_repository

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
    
    # El servicio se encarga de todo y nos devuelve el nombre del grupo
    group_name = _handle(group_service.join_group, user_id, body)
    
    return {"message": f"Te has unido a {group_name} exitosamente"}


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
def create_expense(group_id: int, body: CreateExpenseRequest, user=Depends(get_current_user)):
    user_id = int(user["sub"])
    expense = _handle(expense_service.create_expense, group_id, user_id, body)

    paid_by_user_id = None
    paid_by_name = "Varios pagadores"

    if len(body.payments) == 1:
        paid_by_user_id = body.payments[0].user_id
        payer = user_repository.find_by_id(paid_by_user_id)
        paid_by_name = payer.full_name if payer and payer.full_name else "Administrador"
    
    return ExpenseResponse(
        id=expense.id,
        description=expense.description,
        amount=expense.amount,
        paid_by_user_id=paid_by_user_id,
        paid_by_name=paid_by_name,
        created_at=expense.created_at
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
    )
    for e in expenses
]


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