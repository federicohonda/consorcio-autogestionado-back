from typing import Optional
from src.database.db import get_db_cursor
from src.models.user import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_by_email(email: str) -> Optional[User]:
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (normalize_email(email),))
        row = cur.fetchone()
        return User(**dict(row)) if row else None


def find_by_id(user_id: int) -> Optional[User]:
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return User(**dict(row)) if row else None


def create_user(email: str, hashed_password: Optional[str], full_name: str) -> User:
    with get_db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO users (email, hashed_password, full_name)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (normalize_email(email), hashed_password, full_name),
        )
        row = cur.fetchone()
        return User(**dict(row))
