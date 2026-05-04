from datetime import date
from decimal import Decimal
from typing import Optional

from src.database.db import get_db_cursor
from src.models.payment import OwnerPayment
from src.schemas.payment import OwnerBalanceResponse, AdminPaymentResponse


def create_owner_payment(
    group_id: int,
    user_id: int,
    amount: Decimal,
    receipt_url: str,
    payment_date: Optional[date] = None,
    notes: Optional[str] = None,
) -> OwnerPayment:
    if payment_date is None:
        payment_date = date.today()
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO owner_payments (group_id, user_id, amount, payment_date, receipt_url, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (group_id, user_id, amount, payment_date, receipt_url, notes),
        )
        return OwnerPayment(**dict(cur.fetchone()))


def get_owner_payments(group_id: int, user_id: int) -> list[OwnerPayment]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM owner_payments
            WHERE group_id = %s AND user_id = %s
            ORDER BY payment_date DESC, created_at DESC
            """,
            (group_id, user_id),
        )
        return [OwnerPayment(**dict(r)) for r in cur.fetchall()]


def get_owner_balance(group_id: int, user_id: int, year: int, month: int) -> OwnerBalanceResponse:
    with get_db_cursor() as cur:
        # Parte que le corresponde al usuario este mes
        cur.execute(
            """
            SELECT COALESCE(SUM(es.amount), 0) AS current_month_share
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = %s AND es.user_id = %s
              AND EXTRACT(YEAR  FROM e.expense_date) = %s
              AND EXTRACT(MONTH FROM e.expense_date) = %s
            """,
            (group_id, user_id, year, month),
        )
        current_month_share = Decimal(str(cur.fetchone()["current_month_share"]))

        # Total que le corresponde pagar (todos los tiempos, incluyendo mes actual)
        cur.execute(
            """
            SELECT COALESCE(SUM(es.amount), 0) AS total_owed
            FROM expense_splits es
            JOIN expenses e ON e.id = es.expense_id
            WHERE e.group_id = %s AND es.user_id = %s
            """,
            (group_id, user_id),
        )
        total_owed = Decimal(str(cur.fetchone()["total_owed"]))

        # Total que adelantó de su bolsillo para gastos del edificio (expense_payments).
        # Si pagaste vos el plomero, eso ya es una contribución real al pool.
        cur.execute(
            """
            SELECT COALESCE(SUM(ep.amount_paid), 0) AS total_fronted
            FROM expense_payments ep
            JOIN expenses e ON e.id = ep.expense_id
            WHERE e.group_id = %s AND ep.user_id = %s
            """,
            (group_id, user_id),
        )
        total_fronted = Decimal(str(cur.fetchone()["total_fronted"]))

        # Total transferido directamente al consorcio (owner_payments)
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_transferred
            FROM owner_payments
            WHERE group_id = %s AND user_id = %s
            """,
            (group_id, user_id),
        )
        total_transferred = Decimal(str(cur.fetchone()["total_transferred"]))

        # Distribuciones recibidas del Pozo al avanzar mes
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_distributions
            FROM pozo_distributions
            WHERE group_id = %s AND user_id = %s
            """,
            (group_id, user_id),
        )
        total_distributions = Decimal(str(cur.fetchone()["total_distributions"]))

        # Deudas de aporte mensual acumuladas (no son expense_splits)
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS total_contributions
            FROM contribution_debts
            WHERE group_id = %s AND user_id = %s
            """,
            (group_id, user_id),
        )
        total_contributions = Decimal(str(cur.fetchone()["total_contributions"]))

        # Datos bancarios del consorcio
        cur.execute(
            "SELECT bank_alias, bank_cbu, bank_account_name FROM groups WHERE id = %s",
            (group_id,),
        )
        bank_row = cur.fetchone()

    # Contribución total = lo que adelantaste de tu bolsillo + lo que transferiste al consorcio
    total_contributed = total_fronted + total_transferred

    # Deuda total = expense_splits + aportes mensuales acumulados + lo que el Pozo ya te devolvió
    # (las distribuciones del Pozo cancelan saldo a favor, por eso restan)
    total_owed = total_owed + total_contributions + total_distributions

    # Balance neto: positivo = saldo a favor, negativo = deuda
    net_balance = total_contributed - total_owed

    # Monto sugerido = lo que falta para quedar al día (si net_balance ya es >= 0, no debe nada)
    amount_due = max(Decimal("0"), -net_balance)

    return OwnerBalanceResponse(
        current_month_share=current_month_share,
        net_balance=net_balance,
        amount_due=amount_due,
        bank_alias=bank_row["bank_alias"] if bank_row else None,
        bank_cbu=bank_row["bank_cbu"] if bank_row else None,
        bank_account_name=bank_row["bank_account_name"] if bank_row else None,
    )


def get_all_group_payments(group_id: int) -> list[AdminPaymentResponse]:
    with get_db_cursor() as cur:
        cur.execute(
            """
            SELECT
                op.id, op.user_id, op.amount, op.payment_date,
                op.receipt_url, op.notes, op.created_at,
                u.full_name
            FROM owner_payments op
            JOIN users u ON u.id = op.user_id
            WHERE op.group_id = %s
            ORDER BY op.payment_date DESC, op.created_at DESC
            """,
            (group_id,),
        )
        return [AdminPaymentResponse(**dict(r)) for r in cur.fetchall()]


def update_bank_data(
    group_id: int,
    bank_alias: Optional[str],
    bank_cbu: Optional[str],
    bank_account_name: Optional[str],
) -> None:
    with get_db_cursor() as cur:
        cur.execute(
            """
            UPDATE groups
            SET bank_alias = %s, bank_cbu = %s, bank_account_name = %s
            WHERE id = %s
            """,
            (bank_alias, bank_cbu, bank_account_name, group_id),
        )
