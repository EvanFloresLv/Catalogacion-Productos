# ---------------------------------------------------------------------
# Standard libraries
# ---------------------------------------------------------------------
import logging

# ---------------------------------------------------------------------
# Third-party libraries
# ---------------------------------------------------------------------
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from google.auth import default

# ---------------------------------------------------------------------
# Internal application imports
# ---------------------------------------------------------------------


class LLMSettings(BaseModel):
    provider: str = "gemini"

    model_fast: str = "gemini-2.5-flash"
    model_pro: str = "gemini-2.5-pro"

    temperature: float = 0.7

    embedding_model: str = "text-multilingual-embedding-002"


class GoogleCredentials(BaseModel):
    credentials: object | None = None
    project_id: str | None = None

    @classmethod
    def from_default(cls):
        credentials, project_id = default()
        return cls(credentials=credentials, project_id=project_id)


class GeminiGenerationSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="_",
        env_nested_max_split=2,
        env_prefix="LLM_",
        extra="ignore",
    )

    location: str = "us-central1"
    google: GoogleCredentials = GoogleCredentials.from_default()

    llm: LLMSettings = LLMSettings()


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="_",
        env_nested_max_split=2,
        env_prefix="LOGGING_",
        extra="ignore",
    )

    directory: str = "logs"
    name: str = "app"
    level: str = "INFO"

    module_levels: dict[str, str] = {
        "src": "WARNING",
        "tests": "DEBUG",
    }

    min_level: int = logging.WARNING
    sample_rate: float = 1.0
    deterministic: bool = False

    date_format: str = "%Y-%m-%d_%H:%M:%S"

    base_format: str = "[%(asctime)s] [%(levelname)s] [%(context)s] [trace=%(trace_id)s span=%(span_id)s] - %(message)s"

    log_colors: dict[str, str] = {
        "DEBUG": "white",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red",
    }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "course-notes-ai"
    environment: str = "local"

    # DB
    database_url: str = "sqlite:///./app.db"


settings = Settings()
logging_settings = LoggingSettings()
gemini_settings = GeminiGenerationSettings()