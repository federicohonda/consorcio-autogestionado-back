from decimal import Decimal
from typing import Optional
from src.database.db import get_db_cursor
from src.models.expense import Expense, ExpenseWithPayer
from src.schemas.expense import MonthlySummaryResponse


def create_expense_with_splits(
    group_id: int,
    description: str,
    amount: Decimal,
    paid_by_user_id: int,
    created_by_user_id: int,
    splits: list[dict],
) -> Expense:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO expenses (group_id, description, amount, paid_by_user_id, created_by_user_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (group_id, description, amount, paid_by_user_id, created_by_user_id),
        )
        expense = Expense(**dict(cur.fetchone()))

        for split in splits:
            cur.execute(
                "INSERT INTO expense_splits (expense_id, user_id, amount) VALUES (%s, %s, %s)",
                (expense.id, split["user_id"], split["amount"]),
            )

    return expense


def list_expenses(
    group_id: int, year: int, month: int
) -> list[ExpenseWithPayer]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                e.id, e.group_id, e.description, e.amount,
                e.paid_by_user_id, u.full_name AS paid_by_name, e.created_at
            FROM expenses e
            JOIN users u ON u.id = e.paid_by_user_id
            WHERE e.group_id = %s
              AND EXTRACT(YEAR  FROM e.created_at) = %s
              AND EXTRACT(MONTH FROM e.created_at) = %s
            ORDER BY e.created_at DESC
            """,
            (group_id, year, month),
        )
        return [ExpenseWithPayer(**dict(r)) for r in cur.fetchall()]


def get_user_alltime_balance(group_id: int, user_id: int) -> Decimal:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE(SUM(e.amount) FILTER (WHERE e.paid_by_user_id = %s), 0) AS you_paid,
                COALESCE(SUM(es.amount), 0) AS your_share
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = %s AND es.user_id = %s
            """,
            (user_id, group_id, user_id),
        )
        row = cur.fetchone()
        return Decimal(str(row["you_paid"])) - Decimal(str(row["your_share"]))


def get_monthly_summary(
    group_id: int, user_id: int, year: int, month: int
) -> MonthlySummaryResponse:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_expenses
            FROM expenses
            WHERE group_id = %s
              AND EXTRACT(YEAR  FROM created_at) = %s
              AND EXTRACT(MONTH FROM created_at) = %s
            """,
            (group_id, year, month),
        )
        total_expenses = Decimal(str(cur.fetchone()["total_expenses"]))

        cur.execute(
            """
            SELECT COALESCE(SUM(es.amount), 0) AS your_share
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = %s
              AND es.user_id = %s
              AND EXTRACT(YEAR  FROM e.created_at) = %s
              AND EXTRACT(MONTH FROM e.created_at) = %s
            """,
            (group_id, user_id, year, month),
        )
        your_share = Decimal(str(cur.fetchone()["your_share"]))

        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS you_paid
            FROM expenses
            WHERE group_id = %s
              AND paid_by_user_id = %s
              AND EXTRACT(YEAR  FROM created_at) = %s
              AND EXTRACT(MONTH FROM created_at) = %s
            """,
            (group_id, user_id, year, month),
        )
        you_paid = Decimal(str(cur.fetchone()["you_paid"]))

    your_balance = you_paid - your_share

    return MonthlySummaryResponse(
        year=year,
        month=month,
        total_expenses=total_expenses,
        your_share=your_share,
        you_paid=you_paid,
        your_balance=your_balance,
    )
