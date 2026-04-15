from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="QMAPLOADER_",
        case_sensitive=False,
        extra="ignore",
    )

    primary_port: int = 5786
    fallback_port: int = 8765
    output_dir: str = ""
    tmp_dir: str = ""
    log_level: str = "INFO"

    def resolved_output_dir(self) -> Path:
        if self.output_dir:
            return Path(self.output_dir).expanduser()
        return Path.home() / "Documents" / "QmapLoader" / "outputs"

    def resolved_tmp_dir(self) -> Path:
        if self.tmp_dir:
            return Path(self.tmp_dir).expanduser()
        return PROJECT_ROOT / ".tmp" / "uploads"

    def logs_dir(self) -> Path:
        return PROJECT_ROOT / "logs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
