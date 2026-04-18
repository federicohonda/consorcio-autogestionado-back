from decimal import Decimal, ROUND_HALF_UP
from src.core.exceptions import AppError
from src.core.logger import logger
from src.models.expense import Expense
from src.schemas.expense import CreateExpenseRequest
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository


def create_expense(group_id: int, user_id: int, data: CreateExpenseRequest) -> Expense:
    member = group_repository.get_member(group_id, user_id)
    if not member:
        raise AppError(403, "No sos miembro de este grupo")

    payer = group_repository.get_member(group_id, data.paidByUserId)
    if not payer:
        raise AppError(400, "El pagador no es miembro del grupo")

    members = group_repository.get_members(group_id)
    member_count = len(members)
    if member_count == 0:
        raise AppError(400, "El grupo no tiene miembros")

    unit = Decimal("0.01")
    share = (data.amount / member_count).quantize(unit, rounding=ROUND_HALF_UP)
    splits = [{"user_id": m.user_id, "amount": share} for m in members]

    expense = expense_repository.create_expense_with_splits(
        group_id=group_id,
        description=data.description,
        amount=data.amount,
        paid_by_user_id=data.paidByUserId,
        created_by_user_id=user_id,
        splits=splits,
    )
    logger.info(
        f"Expense created: id={expense.id}, group={group_id}, "
        f"amount={data.amount}, splits={member_count}"
    )
    return expense
