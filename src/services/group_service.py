from src.core.exceptions import AppError
from src.core.logger import logger
from src.models.group import Group
from src.schemas.group import CreateGroupRequest
import src.repositories.group_repository as group_repository
import src.repositories.expense_repository as expense_repository


def create_group(user_id: int, data: CreateGroupRequest) -> Group:
    group = group_repository.create_group(data.name, data.description, data.icon)
    group_repository.add_member(group.id, user_id, "Administrador")
    logger.info(f"Group created: id={group.id}, name={group.name}, admin_user_id={user_id}")
    return group


def join_group(user_id: int, group_id: int) -> None:
    group = group_repository.find_by_id(group_id)
    if not group:
        raise AppError(404, "Grupo no encontrado")

    current_group = group_repository.get_user_group(user_id)
    if current_group:
        if current_group.id == group_id:
            raise AppError(409, "Ya sos miembro de este grupo")
        raise AppError(409, "Ya formás parte de otro grupo. Salí de él antes de unirte a uno nuevo")

    group_repository.add_member(group_id, user_id, "Miembro")
    logger.info(f"User {user_id} joined group {group_id}")


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
