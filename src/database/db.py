import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from src.core.config import settings


@contextmanager
def get_db_cursor():
    conn = psycopg2.connect(settings.database_url)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_connection() -> bool:
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False
