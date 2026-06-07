from decimal import Decimal
from typing import Optional
import secrets
import string
from src.database.db import get_db_cursor
from src.models.group import Group, GroupMember
from src.schemas.group import MemberResponse, MemberWithBalanceResponse


def generate_invite_code(length: int = 6) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_group(name: str, description: Optional[str], icon: str) -> Group:
    invite_code = generate_invite_code()
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO groups (name, description, icon, invite_code) 
            VALUES (%s, %s, %s, %s) RETURNING *
            """,
            (name, description, icon, invite_code),
        )
        return Group(**dict(cur.fetchone()))


def find_by_id(group_id: int) -> Optional[Group]:
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM groups WHERE id = %s", (group_id,))
        row = cur.fetchone()
        return Group(**dict(row)) if row else None


def find_by_invite_code(code: str) -> Optional[Group]:
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM groups WHERE invite_code = %s", (code,))
        row = cur.fetchone()
        return Group(**dict(row)) if row else None


def add_member(group_id: int, user_id: int, role: str, m2: int) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO group_members (group_id, user_id, role, m2) 
            VALUES (%s, %s, %s, %s)
            """,
            (group_id, user_id, role, m2)
        )


def get_members(group_id: int) -> list[MemberResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT gm.user_id, u.full_name, gm.role, gm.joined_at, gm.m2
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = %s
            ORDER BY gm.role DESC, gm.joined_at ASC
            """,
            (group_id,),
        )
        return [MemberResponse(**dict(r)) for r in cur.fetchall()]


def get_members_with_balance(group_id: int) -> list[MemberWithBalanceResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                gm.user_id,
                u.full_name,
                gm.role,
                gm.m2,
                (
                    COALESCE((
                        SELECT SUM(ep.amount_paid)
                        FROM expense_payments ep
                        JOIN expenses e ON e.id = ep.expense_id
                        WHERE e.group_id = gm.group_id AND ep.user_id = gm.user_id
                    ), 0)
                    +
                    COALESCE((
                        SELECT SUM(op.amount)
                        FROM owner_payments op
                        WHERE op.group_id = gm.group_id AND op.user_id = gm.user_id
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(es.amount)
                        FROM expense_splits es
                        JOIN expenses e ON e.id = es.expense_id
                        WHERE e.group_id = gm.group_id AND es.user_id = gm.user_id
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(cd.amount)
                        FROM contribution_debts cd
                        WHERE cd.group_id = gm.group_id AND cd.user_id = gm.user_id
                    ), 0)
                    -
                    COALESCE((
                        SELECT SUM(pd.amount)
                        FROM pozo_distributions pd
                        WHERE pd.group_id = gm.group_id AND pd.user_id = gm.user_id
                    ), 0)
                    +
                    COALESCE((
                        SELECT SUM(ba.amount)
                        FROM balance_adjustments ba
                        WHERE ba.group_id = gm.group_id AND ba.user_id = gm.user_id
                    ), 0)
                ) AS net_balance
            FROM group_members gm
            JOIN users u ON u.id = gm.user_id
            WHERE gm.group_id = %s
            ORDER BY gm.role DESC, u.full_name ASC
            """,
            (group_id,),
        )
        return [MemberWithBalanceResponse(**dict(r)) for r in cur.fetchall()]


def get_member_net_balance(group_id: int, user_id: int) -> Decimal:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE((SELECT SUM(ep.amount_paid) FROM expense_payments ep JOIN expenses e ON e.id = ep.expense_id WHERE e.group_id = %s AND ep.user_id = %s), 0)
                + COALESCE((SELECT SUM(op.amount) FROM owner_payments op WHERE op.group_id = %s AND op.user_id = %s), 0)
                - COALESCE((SELECT SUM(es.amount) FROM expense_splits es JOIN expenses e ON e.id = es.expense_id WHERE e.group_id = %s AND es.user_id = %s), 0)
                - COALESCE((SELECT SUM(cd.amount) FROM contribution_debts cd WHERE cd.group_id = %s AND cd.user_id = %s), 0)
                - COALESCE((SELECT SUM(pd.amount) FROM pozo_distributions pd WHERE pd.group_id = %s AND pd.user_id = %s), 0)
                + COALESCE((SELECT SUM(ba.amount) FROM balance_adjustments ba WHERE ba.group_id = %s AND ba.user_id = %s), 0)
                AS net_balance
            """,
            (group_id, user_id) * 6,
        )
        row = cur.fetchone()
        return Decimal(str(row["net_balance"]))


def insert_balance_adjustment(group_id: int, user_id: int, amount: Decimal, description: str) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO balance_adjustments (group_id, user_id, amount, description)
            VALUES (%s, %s, %s, %s)
            """,
            (group_id, user_id, amount, description),
        )


def remove_members_batch(group_id: int, user_ids: list[int]) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            "DELETE FROM group_members WHERE group_id = %s AND user_id = ANY(%s)",
            (group_id, user_ids),
        )


def update_m2(group_id: int, m2_data: list[dict]) -> None:
    with get_db_cursor() as cur:
        for item in m2_data:
            cur.execute(
                """
                UPDATE group_members 
                SET m2 = %s 
                WHERE group_id = %s AND user_id = %s
                """,
                (item["m2"], group_id, item["user_id"])
            )


def get_member(group_id: int, user_id: int) -> Optional[GroupMember]:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT * FROM group_members WHERE group_id = %s AND user_id = %s",
            (group_id, user_id),
        )
        row = cur.fetchone()
        return GroupMember(**dict(row)) if row else None


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