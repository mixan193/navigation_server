from pydantic_settings import BaseSettings
from pydantic import PostgresDsn, Field


class Settings(BaseSettings):
    # Окружение: production, development, testing
    ENV: str = Field(
        "production",
        env="ENV",
        description="Application environment",
    )
    DEBUG: bool = Field(
        False,
        env="DEBUG",
        description="Turn on debug mode (reload, detailed errors)",
    )

    # Подключение к БД
    DATABASE_URL: PostgresDsn = Field(
        ...,
        env="DATABASE_URL",
    )

    # Общие параметры API
    API_PREFIX: str = Field(
        "/v1",
        env="API_PREFIX",
        description="Base prefix for all API routes",
    )
    APP_NAME: str = Field(
        "Navigation Server",
        env="APP_NAME",
        description="Application name for docs/title",
    )

    # Логи
    LOG_LEVEL: str = Field(
        "INFO",
        env="LOG_LEVEL",
        description="Logging level",
    )
    LOG_DIR: str = Field(
        "logs",
        env="LOG_DIR",
        description="Directory for log files",
    )
    LOG_FILENAME: str = Field(
        "navigation_server.log",
        env="LOG_FILENAME",
        description="Log file name",
    )

    # Pydantic V2: вместо Config используем model_config
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


settings = Settings()
