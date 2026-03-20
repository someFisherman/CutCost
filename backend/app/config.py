from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    database_url: str = "postgresql+psycopg://cutcost:cutcost@localhost:5432/cutcost"
    redis_url: str = "redis://localhost:6379"

    anthropic_api_key: str = ""
    amazon_associate_tag: str = "audix-20"

    environment: str = "development"
    api_base_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    default_buyer_country: str = "CH"
    default_currency: str = "CHF"

    sentry_dsn: str = ""

    # Cost engine defaults
    default_exchange_spread: float = 0.015  # 1.5% bank spread
    swiss_vat_rate: float = 0.081
    swiss_customs_fee: float = 11.50
    swiss_vat_de_minimis: float = 5.0  # VAT not collected if < 5 CHF

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
