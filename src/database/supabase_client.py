from supabase import create_client, Client
from src.core.config import settings
from src.core.logger import logger

_supabase_client: Client | None = None


def get_supabase() -> Client | None:
    global _supabase_client

    if not settings.is_supabase_configured:
        logger.warning("Supabase not configured — storage features disabled")
        return None

    if _supabase_client is None:
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_key)

    return _supabase_client
