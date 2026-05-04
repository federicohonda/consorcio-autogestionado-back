from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from src.core.exceptions import AppError
from src.core.logger import logger
from src.models.expense import Expense
from src.schemas.expense import CreateExpenseRequest
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository
import src.repositories.pozo_repository as pozo_repository


def create_expense(
    group_id: int,
    user_id: int,
    data: CreateExpenseRequest,
    receipt_url: Optional[str] = None,
) -> Expense:
    # 1. Validar que el creador pertenece al grupo
    member = group_repository.get_member(group_id, user_id)
    if not member:
        raise AppError(403, "No sos miembro de este grupo")

    # 2. Gasto pagado por el Pozo (solo admin puede hacerlo)
    if data.paid_by_pozo:
        if member.role.lower() not in ("administrador", "admin"):
            raise AppError(403, "Solo el administrador puede marcar un gasto como pagado por el Pozo")

        settings = pozo_repository.ensure_settings(group_id)
        if settings.pozo_balance < data.amount:
            raise AppError(
                400,
                f"Saldo insuficiente en el Pozo. Disponible: ${settings.pozo_balance:.2f}",
            )

        expense = expense_repository.create_expense_no_splits(
            group_id=group_id,
            created_by_user_id=user_id,
            data=data,
            receipt_url=receipt_url,
        )
        pozo_repository.update_pozo_balance(group_id, -data.amount)
        pozo_repository.create_movement(
            group_id=group_id,
            type="EXPENSE_DEDUCTION",
            amount=data.amount,
            description=data.description,
            expense_id=expense.id,
        )
        logger.info(f"Pozo expense created: id={expense.id}, group={group_id}, amount={data.amount}")
        return expense

    # 3. Validar que TODOS los que pagaron sean miembros del grupo
    for payment in data.payments:
        if not group_repository.get_member(group_id, payment.user_id):
            raise AppError(400, f"El pagador con ID {payment.user_id} no es miembro del grupo")

    members = group_repository.get_members(group_id)
    member_count = len(members)
    if member_count == 0:
        raise AppError(400, "El grupo no tiene miembros")

    # 4. Lógica de División (Deuda)
    unit = Decimal("0.01")
    splits = []

    if data.division_type == "PROPORTIONAL":
        total_m2 = sum(getattr(m, 'm2', 0) for m in members)
        if total_m2 == 0:
            raise AppError(400, "No se puede dividir el gasto porque ninguna unidad tiene metros cuadrados (M2) cargados")

        for m in members:
            member_m2 = getattr(m, 'm2', 0)
            if member_m2 == 0:
                splits.append({"user_id": m.user_id, "amount": Decimal("0.00")})
                continue
            proportion = Decimal(member_m2) / Decimal(total_m2)
            share = (data.amount * proportion).quantize(unit, rounding=ROUND_HALF_UP)
            splits.append({"user_id": m.user_id, "amount": share})
    else:
        share = (data.amount / member_count).quantize(unit, rounding=ROUND_HALF_UP)
        splits = [{"user_id": m.user_id, "amount": share} for m in members]

    # 5. Ajuste de centavos
    total_splits = sum(s["amount"] for s in splits)
    if total_splits != data.amount:
        diff = data.amount - total_splits
        splits[0]["amount"] += diff

    # 6. Guardar en Base de Datos
    expense = expense_repository.create_expense_with_splits_v2(
        group_id=group_id,
        created_by_user_id=user_id,
        data=data,
        splits=splits,
        receipt_url=receipt_url,
    )

    logger.info(
        f"Expense V2 created: id={expense.id}, group={group_id}, "
        f"amount={data.amount}, splits={member_count}, receipt={bool(receipt_url)}"
    )
    return expense