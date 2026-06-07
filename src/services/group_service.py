from decimal import Decimal
from src.core.exceptions import AppError
from src.core.logger import logger
from src.models.group import Group
from src.schemas.group import CreateGroupRequest
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository
from src.schemas.group import JoinGroupRequest


def create_group(user_id: int, data: CreateGroupRequest) -> Group:
    group = group_repository.create_group(data.name, data.description, data.icon)
    group_repository.add_member(group.id, user_id, "Administrador", data.m2)
    logger.info(f"Group created: id={group.id}, name={group.name}, admin_user_id={user_id}, m2={data.m2}, invite_code={group.invite_code}")
    return group


def join_group(user_id: int, data: JoinGroupRequest) -> str:
    group = group_repository.find_by_invite_code(data.invite_code)
    if not group:
        raise AppError(404, "Código de invitación inválido o consorcio no encontrado")

    existing_member = group_repository.get_member(group.id, user_id)
    if existing_member:
        raise AppError(400, "Ya sos miembro de este consorcio")

    group_repository.add_member(
        group_id=group.id, 
        user_id=user_id, 
        role="Miembro", 
        m2=data.m2
    )

    logger.info(f"User {user_id} joined group {group.id} via invite code")
    return group.name


def leave_group(group_id: int, user_id: int) -> None:
    member = group_repository.get_member(group_id, user_id)
    if not member:
        raise AppError(404, "No sos miembro de este grupo")

    if member.role == "Administrador":
        members = group_repository.get_members(group_id)
        if len(members) > 1:
            raise AppError(400, "Transferí el rol de Administrador a otro miembro antes de salir")

    balance = expense_repository.get_user_alltime_balance(group_id, user_id)
    if balance < -0.01:
        raise AppError(
            400,
            f"Tenés un saldo pendiente de ${abs(balance):.2f}. Saldalo antes de salir del grupo",
        )

    group_repository.remove_member(group_id, user_id)
    logger.info(f"User {user_id} left group {group_id}")


def remove_members(group_id: int, requesting_user_id: int, user_ids_to_remove: list[int]) -> None:
    requester = group_repository.get_member(group_id, requesting_user_id)
    if not requester or requester.role != "Administrador":
        raise AppError(403, "Solo el Administrador puede eliminar socios")

    if requesting_user_id in user_ids_to_remove:
        raise AppError(400, "No podés eliminarte a vos mismo")

    all_members = group_repository.get_members(group_id)
    member_ids = {m.user_id for m in all_members}
    for uid in user_ids_to_remove:
        if uid not in member_ids:
            raise AppError(404, f"El usuario {uid} no es miembro del grupo")

    remaining = [m for m in all_members if m.user_id not in set(user_ids_to_remove)]
    total_remaining_m2 = sum(m.m2 or 0 for m in remaining)

    if total_remaining_m2 > 0:
        for uid in user_ids_to_remove:
            balance = group_repository.get_member_net_balance(group_id, uid)
            if balance == Decimal("0"):
                continue
            for rem in remaining:
                rem_m2 = rem.m2 or 0
                if rem_m2 == 0:
                    continue
                proportion = Decimal(str(rem_m2)) / Decimal(str(total_remaining_m2))
                adjustment = balance * proportion
                removed_member = next(m for m in all_members if m.user_id == uid)
                group_repository.insert_balance_adjustment(
                    group_id,
                    rem.user_id,
                    adjustment,
                    f"Redistribución por baja de {removed_member.full_name}",
                )

    group_repository.remove_members_batch(group_id, user_ids_to_remove)
    logger.info(f"Members {user_ids_to_remove} removed from group {group_id} by user {requesting_user_id}")


def transfer_admin(group_id: int, requesting_user_id: int, new_admin_user_id: int) -> None:
    requester = group_repository.get_member(group_id, requesting_user_id)
    if not requester or requester.role != "Administrador":
        raise AppError(403, "Solo el Administrador puede transferir el rol")

    new_admin = group_repository.get_member(group_id, new_admin_user_id)
    if not new_admin:
        raise AppError(404, "El usuario no es miembro del grupo")

    group_repository.update_member_role(group_id, requesting_user_id, "Miembro")
    group_repository.update_member_role(group_id, new_admin_user_id, "Administrador")
    logger.info(
        f"Admin transferred in group {group_id}: "
        f"from user {requesting_user_id} to user {new_admin_user_id}"
    )
