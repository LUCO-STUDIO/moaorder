from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://moaorder:moaorder@localhost:5433/moaorder"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_EXPIRE_DAYS: int = 7

    # Kakao OAuth
    KAKAO_CLIENT_ID: str = ""
    KAKAO_CLIENT_SECRET: str = ""
    KAKAO_REDIRECT_URI: str = "http://localhost:5173/auth/kakao/callback"

    # PortOne
    PORTONE_STORE_ID: str = ""
    PORTONE_API_SECRET: str = ""
    PORTONE_CHANNEL_KEY: str = ""

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = ""
    R2_PUBLIC_BASE_URL: str = ""

    # Email (Resend)
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = ""
    EMAIL_REPLY_TO: str = ""

    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"

    # Ops alerts (Discord webhook URL). Empty value disables alerting.
    DISCORD_OPS_WEBHOOK_URL: str = ""

    # Testing
    TESTING: bool = False

    # CORS
    CORS_ORIGINS: list[str] = [
        "https://moaorder.com",
        "https://www.moaorder.com",
        "http://localhost:5173",
    ]


settings = Settings()
