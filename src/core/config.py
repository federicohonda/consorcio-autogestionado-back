from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "consorcio-autogestionado-back"
    environment: str = "development"
    port: int = 8000
    debug: bool = False

    jwt_secret: str
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    database_url: str

    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    uploads_dir: str = "uploads"
    max_receipt_size_bytes: int = 10 * 1024 * 1024  # 10 MB

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


settings = Settings()
