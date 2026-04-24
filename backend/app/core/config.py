from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql://localhost/edgeboard_dev"
    news_api_key: str = ""
    app_env: str = "development"
    app_port: int = 8000

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


settings = Settings()
