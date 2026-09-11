"""Configuración tipada de la aplicación, leída desde variables de entorno.

Las variables obligatorias (`SECRET_KEY`, `MONGODB_URL`, `MONGODB_DB_NAME`)
no tienen valor por defecto: si faltan, `Settings()` lanza `ValidationError`
de inmediato (fail-fast). `get_settings()` las instancia de forma perezosa
—no al importar este módulo— para que los tests que no dependen de
configuración puedan correr sin necesitar un `.env` presente.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno de la Mesa de Ayuda (ver `.env.example`)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SECRET_KEY: str
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    ALGORITHM: str = "HS256"
    EXPIRACION_MINUTOS: int = 60


@lru_cache
def get_settings() -> Settings:
    """Instancia (y cachea) la configuración; falla rápido si falta algo obligatorio."""
    return Settings()  # type: ignore[call-arg]
