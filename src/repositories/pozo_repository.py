from decimal import Decimal
from typing import Optional

from src.database.db import get_db_cursor
from src.models.pozo import GroupSettings, PozoMovement
from src.schemas.pozo import PozoMovementResponse


def get_settings(group_id: int) -> Optional[GroupSettings]:
    with get_db_cursor() as cur:
        cur.execute(
            "SELECT * FROM group_settings WHERE group_id = %s",
            (group_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return GroupSettings(**dict(row))


def ensure_settings(group_id: int) -> GroupSettings:
    """Gets settings, creating a default row if it doesn't exist yet."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO group_settings (group_id, active_month, monthly_contribution, pozo_balance)
            VALUES (
                %s,
                EXTRACT(YEAR FROM NOW())::int * 100 + EXTRACT(MONTH FROM NOW())::int,
                0, 0
            )
            ON CONFLICT (group_id) DO UPDATE SET updated_at = group_settings.updated_at
            RETURNING *
            """,
            (group_id,),
        )
        return GroupSettings(**dict(cur.fetchone()))


def update_pozo_balance(group_id: int, delta: Decimal) -> Decimal:
    """Atomically adds delta (positive or negative) to pozo_balance. Returns new balance."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE group_settings
            SET pozo_balance = pozo_balance + %s, updated_at = NOW()
            WHERE group_id = %s
            RETURNING pozo_balance
            """,
            (delta, group_id),
        )
        row = cur.fetchone()
        return Decimal(str(row["pozo_balance"])) if row else Decimal("0")


def update_monthly_contribution(group_id: int, amount: Decimal) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE group_settings
            SET monthly_contribution = %s, updated_at = NOW()
            WHERE group_id = %s
            """,
            (amount, group_id),
        )


def advance_active_month(group_id: int) -> int:
    """Advances active_month by 1 month (handles year rollover). Returns new YYYYMM."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE group_settings
            SET active_month = (
                CASE
                    WHEN MOD(active_month, 100) = 12
                    THEN (active_month / 100 + 1) * 100 + 1
                    ELSE active_month + 1
                END
            ),
            updated_at = NOW()
            WHERE group_id = %s
            RETURNING active_month
            """,
            (group_id,),
        )
        row = cur.fetchone()
        return int(row["active_month"]) if row else 0


def create_movement(
    group_id: int,
    type: str,
    amount: Decimal,
    description: Optional[str] = None,
    user_id: Optional[int] = None,
    expense_id: Optional[int] = None,
) -> PozoMovement:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO pozo_movements (group_id, type, amount, description, user_id, expense_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (group_id, type, amount, description, user_id, expense_id),
        )
        return PozoMovement(**dict(cur.fetchone()))


def get_movements(group_id: int, limit: int = 20) -> list[PozoMovementResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                pm.id,
                pm.type,
                pm.amount,
                pm.description,
                pm.created_at,
                u.full_name AS user_name
            FROM pozo_movements pm
            LEFT JOIN users u ON u.id = pm.user_id
            WHERE pm.group_id = %s
            ORDER BY pm.created_at DESC
            LIMIT %s
            """,
            (group_id, limit),
        )
        return [PozoMovementResponse(**dict(r)) for r in cur.fetchall()]


def create_distribution(
    group_id: int,
    user_id: int,
    amount: Decimal,
    month_year: int,
) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO pozo_distributions (group_id, user_id, amount, month_year)
            VALUES (%s, %s, %s, %s)
            """,
            (group_id, user_id, amount, month_year),
        )


def get_total_distributions(group_id: int, user_id: int) -> Decimal:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM pozo_distributions
            WHERE group_id = %s AND user_id = %s
            """,
            (group_id, user_id),
        )
        return Decimal(str(cur.fetchone()["total"]))


def create_contribution_debts(
    group_id: int,
    member_ids: list[int],
    amount_per_member: Decimal,
    month_year: int,
) -> None:
    """Creates one contribution_debt row per member for the given month.
    Uses ON CONFLICT DO NOTHING so re-running is safe."""
    with get_db_cursor() as cur:
        for user_id in member_ids:
            cur.execute(
                """
                INSERT INTO contribution_debts (group_id, user_id, amount, month_year)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (group_id, user_id, month_year) DO NOTHING
                """,
                (group_id, user_id, amount_per_member, month_year),
            )
