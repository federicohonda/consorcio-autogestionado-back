from typing import Optional
from src.database.db import get_db_cursor
from src.models.group import Group, GroupMember, GroupWithMeta
from src.schemas.group import MemberResponse


def create_group(name: str, description: Optional[str], icon: str) -> Group:
    with get_db_cursor() as cur:
        cur.execute(
            "INSERT INTO groups (name, description, icon) VALUES (%s, %s, %s) RETURNING *",
            (name, description, icon),
        )
        return Group(**dict(cur.fetchone()))


def find_all_groups() -> list[GroupWithMeta]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                g.id, g.name, g.description, g.icon, g.created_at,
                COUNT(gm.id) AS member_count,
                u.full_name AS admin_name
            FROM groups g
            LEFT JOIN group_members gm ON gm.group_id = g.id
            LEFT JOIN group_members adm ON adm.group_id = g.id AND adm.role = 'Administrador'
            LEFT JOIN users u ON u.id = adm.user_id
            GROUP BY g.id, u.full_name
            ORDER BY g.created_at DESC
            """,
        )
        rows = cur.fetchall()
        return [
            GroupWithMeta(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                icon=r["icon"],
                member_count=r["member_count"],
                admin_name=r["admin_name"],
                created_at=r["created_at"],
            )
            for r in rows
        ]


def find_by_id(group_id: int) -> Optional[Group]:
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM groups WHERE id = %s", (group_id,))
        row = cur.fetchone()
        return Group(**dict(row)) if row else None


def add_member(group_id: int, user_id: int, role: str) -> GroupMember:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO group_members (group_id, user_id, role)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (group_id, user_id, role),
        )
        return GroupMember(**dict(cur.fetchone()))


def get_members(group_id: int) -> list[MemberResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT gm.user_id, u.full_name, gm.role, gm.joined_at
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = %s
            ORDER BY gm.role DESC, gm.joined_at ASC
            """,
            (group_id,),
        )
        return [MemberResponse(**dict(r)) for r in cur.fetchall()]


def get_member(group_id: int, user_id: int) -> Optional[GroupMember]:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT * FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )
        row = cur.fetchone()
        return GroupMember(**dict(row)) if row else None


def remove_member(group_id: int, user_id: int) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            "DELETE FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )


def update_member_role(group_id: int, user_id: int, new_role: str) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            "UPDATE group_members SET role = %s WHERE group_id = %s AND user_id = %s",
            (new_role, group_id, user_id),
        )


def get_user_group(user_id: int) -> Optional[Group]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT g.*
            FROM groups g
            JOIN group_members gm ON gm.group_id = g.id
            WHERE gm.user_id = %s
            LIMIT 1
            """,
            (user_id,),
        )
        row = cur.fetchone()
        return Group(**dict(row)) if row else None
