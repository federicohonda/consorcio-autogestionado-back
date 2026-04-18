from pathlib import Path
import psycopg2
from src.core.config import settings
from src.core.logger import logger


def run_migrations() -> None:
    migrations_dir = Path(__file__).parent.parent.parent / "supabase" / "migrations"
    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        logger.info("No migrations found — skipping")
        return

    conn = psycopg2.connect(settings.database_url)
    try:
        for sql_file in sql_files:
            logger.info(f"Applying migration: {sql_file.name}")
            with conn.cursor() as cur:
                cur.execute(sql_file.read_text())
            conn.commit()
            logger.info(f"✓ {sql_file.name}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run_migrations()
