import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File, Query

from src.core.dependencies import get_current_user
import src.repositories.payment_repository as payment_repository
import src.repositories.group_repository as group_repository
import src.repositories.pozo_repository as pozo_repository
import src.services.receipt_service as receipt_service
from src.schemas.payment import (
    OwnerBalanceResponse,
    OwnerPaymentResponse,
    AdminPaymentResponse,
    CreateOwnerPaymentRequest,
    UpdateBankDataRequest,
)

router = APIRouter(prefix="/groups", tags=["payments"])


def _require_group(group_id: int):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")


@router.get("/{group_id}/payments/balance", response_model=OwnerBalanceResponse)
def get_owner_balance(
    group_id: int,
    year: Optional[int] = Query(default=None),
    month: Optional[int] = Query(default=None),
    user=Depends(get_current_user),
):
    _require_group(group_id)
    user_id = int(user["sub"])
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month
    return payment_repository.get_owner_balance(group_id, user_id, year, month)


@router.post("/{group_id}/payments", status_code=201, response_model=OwnerPaymentResponse)
async def create_owner_payment(
    group_id: int,
    payment_data: str = Form(..., description="JSON con amount, payment_date, notes"),
    receipt: UploadFile = File(..., description="Comprobante obligatorio (imagen o PDF)"),
    user=Depends(get_current_user),
):
    _require_group(group_id)
    user_id = int(user["sub"])

    try:
        body = CreateOwnerPaymentRequest(**json.loads(payment_data))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Error de validación: {str(e)}")

    if not receipt or not receipt.filename:
        raise HTTPException(status_code=400, detail="El comprobante es obligatorio")

    receipt_url = await receipt_service.save_receipt(receipt)

    payment = payment_repository.create_owner_payment(
        group_id=group_id,
        user_id=user_id,
        amount=body.amount,
        receipt_url=receipt_url,
        payment_date=body.payment_date,
        notes=body.notes,
    )

    # Todo pago ingresa automáticamente al Pozo
    pozo_repository.ensure_settings(group_id)
    pozo_repository.update_pozo_balance(group_id, body.amount)
    pozo_repository.create_movement(
        group_id=group_id,
        type="PAYMENT_INCOME",
        amount=body.amount,
        user_id=user_id,
    )

    return OwnerPaymentResponse(
        id=payment.id,
        amount=payment.amount,
        payment_date=payment.payment_date,
        receipt_url=payment.receipt_url,
        notes=payment.notes,
        created_at=payment.created_at,
    )


@router.get("/{group_id}/payments/all", response_model=list[AdminPaymentResponse])
def list_all_payments(
    group_id: int,
    user=Depends(get_current_user),
):
    _require_group(group_id)
    user_id = int(user["sub"])
    member = group_repository.get_member(group_id, user_id)
    if not member or member.role.lower() not in ("administrador", "admin"):
        raise HTTPException(status_code=403, detail="Solo el administrador puede ver todos los pagos")
    return payment_repository.get_all_group_payments(group_id)


@router.get("/{group_id}/payments", response_model=list[OwnerPaymentResponse])
def list_owner_payments(
    group_id: int,
    user=Depends(get_current_user),
):
    _require_group(group_id)
    user_id = int(user["sub"])
    payments = payment_repository.get_owner_payments(group_id, user_id)
    return [
        OwnerPaymentResponse(
            id=p.id,
            amount=p.amount,
            payment_date=p.payment_date,
            receipt_url=p.receipt_url,
            notes=p.notes,
            created_at=p.created_at,
        )
        for p in payments
    ]


@router.patch("/{group_id}/bank-data", status_code=200)
def update_bank_data(
    group_id: int,
    body: UpdateBankDataRequest,
    user=Depends(get_current_user),
):
    _require_group(group_id)
    user_id = int(user["sub"])
    member = group_repository.get_member(group_id, user_id)
    if not member or member.role.lower() not in ("administrador", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Solo el administrador puede actualizar los datos bancarios",
        )
    payment_repository.update_bank_data(
        group_id=group_id,
        bank_alias=body.bank_alias,
        bank_cbu=body.bank_cbu,
        bank_account_name=body.bank_account_name,
    )
    return {"message": "Datos bancarios actualizados correctamente"}
