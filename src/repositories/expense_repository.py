from decimal import Decimal
from typing import Optional
from src.database.db import get_db_cursor
from src.models.expense import Expense, ExpenseWithPayer
from src.schemas.expense import MonthlySummaryResponse, CreateExpenseRequest

def _insert_expense_base(cur, group_id: int, created_by_user_id: int, data: CreateExpenseRequest, receipt_url: Optional[str]) -> Expense:
    cur.execute(
        """
        INSERT INTO expenses (
            group_id, description, amount, category,
            expense_date, division_type, receipt_url, created_by_user_id, paid_by_pozo
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            group_id, data.description, data.amount, data.category,
            data.expense_date, data.division_type, receipt_url, created_by_user_id,
            data.paid_by_pozo,
        ),
    )
    expense_row = dict(cur.fetchone())
    if 'paid_by_user_id' not in expense_row:
        expense_row['paid_by_user_id'] = None
    return Expense(**expense_row)


def create_expense_with_splits_v2(
    group_id: int,
    created_by_user_id: int,
    data: CreateExpenseRequest,
    splits: list[dict],
    receipt_url: Optional[str] = None,
) -> Expense:
    with get_db_cursor() as cur:
        expense = _insert_expense_base(cur, group_id, created_by_user_id, data, receipt_url)

        for payment in data.payments:
            cur.execute(
                "INSERT INTO expense_payments (expense_id, user_id, amount_paid) VALUES (%s, %s, %s)",
                (expense.id, payment.user_id, payment.amount),
            )

        for split in splits:
            cur.execute(
                "INSERT INTO expense_splits (expense_id, user_id, amount) VALUES (%s, %s, %s)",
                (expense.id, split["user_id"], split["amount"]),
            )

    return expense


def create_expense_no_splits(
    group_id: int,
    created_by_user_id: int,
    data: CreateExpenseRequest,
    receipt_url: Optional[str] = None,
) -> Expense:
    """Creates an expense paid by the Pozo — no splits, no individual payers."""
    with get_db_cursor() as cur:
        expense = _insert_expense_base(cur, group_id, created_by_user_id, data, receipt_url)
    return expense


def create_monthly_contribution(
    group_id: int,
    created_by_user_id: int,
    description: str,
    amount: Decimal,
    expense_date,
    splits: list[dict],
) -> Expense:
    """Creates the automatic monthly contribution expense bypassing Pydantic validation."""
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO expenses (
                group_id, description, amount, category,
                expense_date, division_type, receipt_url, created_by_user_id, paid_by_pozo
            )
            VALUES (%s, %s, %s, 'Otros', %s, 'EQUALLY', NULL, %s, FALSE)
            RETURNING *
            """,
            (group_id, description, amount, expense_date, created_by_user_id),
        )
        expense_row = dict(cur.fetchone())
        expense_row.setdefault('paid_by_user_id', None)
        expense = Expense(**expense_row)

        for split in splits:
            cur.execute(
                "INSERT INTO expense_splits (expense_id, user_id, amount) VALUES (%s, %s, %s)",
                (expense.id, split["user_id"], split["amount"]),
            )
    return expense

def list_expenses(group_id: int, year: int, month: int) -> list[ExpenseWithPayer]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                e.id, e.group_id, e.description, e.amount, e.category, e.created_at,
                e.receipt_url, e.paid_by_pozo,
                (SELECT user_id FROM expense_payments WHERE expense_id = e.id LIMIT 1) as paid_by_user_id,
                CASE
                    WHEN e.paid_by_pozo THEN 'el Pozo'
                    ELSE (
                        SELECT CASE
                            WHEN COUNT(*) = 1 THEN MAX(u.full_name)
                            WHEN COUNT(*) > 1 THEN MAX(u.full_name) || ' y ' || (COUNT(*) - 1)::text || ' más'
                            ELSE 'Sin pagos'
                        END
                        FROM expense_payments ep
                        JOIN users u ON u.id = ep.user_id
                        WHERE ep.expense_id = e.id
                    )
                END AS paid_by_name
            FROM expenses e
            WHERE e.group_id = %s
              AND EXTRACT(YEAR  FROM e.expense_date) = %s
              AND EXTRACT(MONTH FROM e.expense_date) = %s
            ORDER BY e.expense_date DESC, e.created_at DESC
            """,
            (group_id, year, month),
        )
        return [ExpenseWithPayer(**dict(r)) for r in cur.fetchall()]

def get_user_alltime_balance(group_id: int, user_id: int) -> Decimal:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                COALESCE((SELECT SUM(amount_paid) FROM expense_payments ep JOIN expenses e2 ON e2.id = ep.expense_id WHERE e2.group_id = %s AND ep.user_id = %s), 0) AS you_paid,
                COALESCE((SELECT SUM(amount) FROM expense_splits es JOIN expenses e3 ON e3.id = es.expense_id WHERE e3.group_id = %s AND es.user_id = %s), 0) AS your_share
            """,
            (group_id, user_id, group_id, user_id),
        )
        row = cur.fetchone()
        return Decimal(str(row["you_paid"])) - Decimal(str(row["your_share"]))

def get_monthly_summary(group_id: int, user_id: int, year: int, month: int) -> MonthlySummaryResponse:
    with get_db_cursor() as cur:
        # Total gastado en el consorcio ese mes
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_expenses
            FROM expenses
            WHERE group_id = %s
              AND EXTRACT(YEAR  FROM expense_date) = %s
              AND EXTRACT(MONTH FROM expense_date) = %s
            """,
            (group_id, year, month),
        )
        total_expenses = Decimal(str(cur.fetchone()["total_expenses"]))

        # Parte de la deuda que le toca al usuario
        cur.execute(
            """
            SELECT COALESCE(SUM(es.amount), 0) AS your_share
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = %s AND es.user_id = %s
              AND EXTRACT(YEAR  FROM e.expense_date) = %s
              AND EXTRACT(MONTH FROM e.expense_date) = %s
            """,
            (group_id, user_id, year, month),
        )
        your_share = Decimal(str(cur.fetchone()["your_share"]))

        # Cuánta plata puso el usuario de su bolsillo
        cur.execute(
            """
            SELECT COALESCE(SUM(ep.amount_paid), 0) AS you_paid
            FROM expense_payments ep
            JOIN expenses e ON e.id = ep.expense_id
            WHERE e.group_id = %s AND ep.user_id = %s
              AND EXTRACT(YEAR  FROM e.expense_date) = %s
              AND EXTRACT(MONTH FROM e.expense_date) = %s
            """,
            (group_id, user_id, year, month),
        )
        you_paid = Decimal(str(cur.fetchone()["you_paid"]))

        # Balance histórico acumulado (misma lógica que get_members_with_balance).
        # "Tu balance" no se reinicia mes a mes: refleja toda la deuda/crédito histórica.
        cur.execute(
            """
            SELECT
                COALESCE((
                    SELECT SUM(ep.amount_paid)
                    FROM expense_payments ep
                    JOIN expenses e2 ON e2.id = ep.expense_id
                    WHERE e2.group_id = %s AND ep.user_id = %s
                ), 0)
                +
                COALESCE((
                    SELECT SUM(op.amount)
                    FROM owner_payments op
                    WHERE op.group_id = %s AND op.user_id = %s
                ), 0)
                -
                COALESCE((
                    SELECT SUM(es.amount)
                    FROM expense_splits es
                    JOIN expenses e3 ON e3.id = es.expense_id
                    WHERE e3.group_id = %s AND es.user_id = %s
                ), 0)
                -
                COALESCE((
                    SELECT SUM(cd.amount)
                    FROM contribution_debts cd
                    WHERE cd.group_id = %s AND cd.user_id = %s
                ), 0)
                -
                COALESCE((
                    SELECT SUM(pd.amount)
                    FROM pozo_distributions pd
                    WHERE pd.group_id = %s AND pd.user_id = %s
                ), 0) AS net_balance
            """,
            (group_id, user_id) * 5,
        )
        your_balance = Decimal(str(cur.fetchone()["net_balance"]))

    return MonthlySummaryResponse(
        year=year,
        month=month,
        total_expenses=total_expenses,
        your_share=your_share,
        you_paid=you_paid,
        your_balance=your_balance,
    )