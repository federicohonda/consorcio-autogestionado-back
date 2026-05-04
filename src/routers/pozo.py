from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException

from src.core.dependencies import get_current_user
import src.repositories.group_repository as group_repository
import src.repositories.pozo_repository as pozo_repository
from src.schemas.pozo import PozoResponse, UpdatePozoConfigRequest, AdvanceMonthResponse

router = APIRouter(prefix="/groups", tags=["pozo"])

MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _require_admin(group_id: int, user_id: int):
    member = group_repository.get_member(group_id, user_id)
    if not member or member.role.lower() not in ("administrador", "admin"):
        raise HTTPException(status_code=403, detail="Solo el administrador puede realizar esta acción")
    return member


@router.get("/{group_id}/pozo", response_model=PozoResponse)
def get_pozo(group_id: int, user=Depends(get_current_user)):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    settings = pozo_repository.ensure_settings(group_id)
    movements = pozo_repository.get_movements(group_id)
    return PozoResponse(
        balance=settings.pozo_balance,
        monthly_contribution=settings.monthly_contribution,
        active_month=settings.active_month,
        movements=movements,
    )


@router.patch("/{group_id}/pozo/config", status_code=200)
def update_pozo_config(group_id: int, body: UpdatePozoConfigRequest, user=Depends(get_current_user)):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    user_id = int(user["sub"])
    _require_admin(group_id, user_id)
    pozo_repository.update_monthly_contribution(group_id, body.monthly_contribution)
    return {"message": "Aporte mensual actualizado correctamente"}


@router.post("/{group_id}/pozo/advance-month", response_model=AdvanceMonthResponse)
def advance_month(group_id: int, user=Depends(get_current_user)):
    if not group_repository.find_by_id(group_id):
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    user_id = int(user["sub"])
    _require_admin(group_id, user_id)

    settings = pozo_repository.ensure_settings(group_id)
    current_month = settings.active_month
    pozo_balance = settings.pozo_balance
    monthly_contribution = settings.monthly_contribution

    # 1. Obtener balances actuales de todos los miembros
    members_with_balance = group_repository.get_members_with_balance(group_id)

    # 2. Identificar acreedores (saldo a favor > 0)
    creditors = [m for m in members_with_balance if m.net_balance > Decimal("0.01")]
    total_credit = sum(m.net_balance for m in creditors)

    # 3. Distribuir el Pozo entre los acreedores
    distributed = Decimal("0")
    unit = Decimal("0.01")

    if creditors and pozo_balance > Decimal("0"):
        if pozo_balance >= total_credit:
            # Alcanza para pagar todo
            for creditor in creditors:
                pozo_repository.create_distribution(
                    group_id=group_id,
                    user_id=creditor.user_id,
                    amount=creditor.net_balance.quantize(unit, rounding=ROUND_HALF_UP),
                    month_year=current_month,
                )
            distributed = total_credit
        else:
            # Distribución proporcional
            for creditor in creditors:
                share = (creditor.net_balance * pozo_balance / total_credit).quantize(unit, rounding=ROUND_HALF_UP)
                if share > Decimal("0.01"):
                    pozo_repository.create_distribution(
                        group_id=group_id,
                        user_id=creditor.user_id,
                        amount=share,
                        month_year=current_month,
                    )
                    distributed += share

    # 4. Descontar del Pozo lo distribuido
    if distributed > Decimal("0"):
        pozo_repository.update_pozo_balance(group_id, -distributed)
        pozo_repository.create_movement(
            group_id=group_id,
            type="MONTH_DISTRIBUTION",
            amount=distributed,
            description=f"Distribución al cerrar {_format_month(current_month)}",
        )

    # 5. Avanzar el mes
    new_month = pozo_repository.advance_active_month(group_id)

    # 6. Si hay aporte mensual configurado, crear deudas individuales para el nuevo mes
    # No se crea un "gasto": los aportes no aparecen en la lista de gastos ni suman al Total del mes.
    # Se acumulan mes a mes en contribution_debts hasta que cada miembro los pague via owner_payment.
    if monthly_contribution > Decimal("0"):
        members = group_repository.get_members(group_id)
        if members:
            share = monthly_contribution.quantize(unit, rounding=ROUND_HALF_UP)
            pozo_repository.create_contribution_debts(
                group_id=group_id,
                member_ids=[m.user_id for m in members],
                amount_per_member=share,
                month_year=new_month,
            )

    # 7. Obtener balance final del Pozo
    updated_settings = pozo_repository.get_settings(group_id)
    new_balance = updated_settings.pozo_balance if updated_settings else Decimal("0")

    return AdvanceMonthResponse(
        active_month=new_month,
        distributed_amount=distributed,
        beneficiaries_count=len([c for c in creditors if distributed > Decimal("0")]) if creditors else 0,
        new_balance=new_balance,
        message=f"Mes avanzado correctamente a {_format_month(new_month)}. Se distribuyeron ${distributed:,.2f} entre {len(creditors)} socios.",
    )


def _format_month(yyyymm: int) -> str:
    year = yyyymm // 100
    month = yyyymm % 100
    return f"{MONTH_NAMES[month - 1]} {year}"
