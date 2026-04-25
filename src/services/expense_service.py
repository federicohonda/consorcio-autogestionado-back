from decimal import Decimal, ROUND_HALF_UP
from src.core.exceptions import AppError
from src.core.logger import logger
from src.models.expense import Expense
from src.schemas.expense import CreateExpenseRequest
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository

def create_expense(group_id: int, user_id: int, data: CreateExpenseRequest) -> Expense:
    # 1. Validar que el creador pertenece al grupo
    member = group_repository.get_member(group_id, user_id)
    if not member:
        raise AppError(403, "No sos miembro de este grupo")

    # 2. Validar que TODOS los que pagaron sean miembros del grupo
    for payment in data.payments:
        if not group_repository.get_member(group_id, payment.user_id):
            raise AppError(400, f"El pagador con ID {payment.user_id} no es miembro del grupo")

    members = group_repository.get_members(group_id)
    member_count = len(members)
    if member_count == 0:
        raise AppError(400, "El grupo no tiene miembros")

    # 3. Lógica de División (Deuda)
    unit = Decimal("0.01")
    splits = []

    if data.division_type == "PROPORTIONAL":
        # 1. Obtenemos el total de M2 del edificio sumando a los miembros actuales
        total_m2 = sum(getattr(m, 'm2', 0) for m in members)
        
        if total_m2 == 0:
            raise AppError(400, "No se puede dividir el gasto porque ninguna unidad tiene metros cuadrados (M2) cargados")

        for m in members:
            member_m2 = getattr(m, 'm2', 0)
            
            # 2. Si alguien tiene 0 m2, su deuda es 0
            if member_m2 == 0:
                splits.append({"user_id": m.user_id, "amount": Decimal("0.00")})
                continue
                
            # 3. Regla de tres simple: (Mis M2 / M2 Totales) * Monto del Gasto
            proportion = Decimal(member_m2) / Decimal(total_m2)
            share = (data.amount * proportion).quantize(unit, rounding=ROUND_HALF_UP)
            splits.append({"user_id": m.user_id, "amount": share})
            
    else:
        # Partes iguales (queda igual que antes)
        share = (data.amount / member_count).quantize(unit, rounding=ROUND_HALF_UP)
        splits = [{"user_id": m.user_id, "amount": share} for m in members]

    # 4. Ajuste de centavos (Rounding error fix)
    total_splits = sum(s["amount"] for s in splits)
    if total_splits != data.amount:
        diff = data.amount - total_splits
        splits[0]["amount"] += diff 

    # 5. Guardar en Base de Datos
    expense = expense_repository.create_expense_with_splits_v2(
        group_id=group_id,
        created_by_user_id=user_id,
        data=data,
        splits=splits,
    )
    
    logger.info(
        f"Expense V2 created: id={expense.id}, group={group_id}, "
        f"amount={data.amount}, splits={member_count}"
    )
    return expense