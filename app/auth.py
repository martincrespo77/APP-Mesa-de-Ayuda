"""Utilidades de autenticación: hashing de contraseñas (bcrypt) y JWT.

Es infraestructura de seguridad, no dominio: `TokenInvalidoError` no hereda
de `DominioError` porque un JWT inválido no es una regla de negocio
violada, sino un problema de la capa de presentación/seguridad.
"""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.compartido.dominio import RolUsuario
from app.config import get_settings


class TokenInvalidoError(Exception):
    """Lanzada cuando un JWT es inválido, está expirado o fue manipulado."""


def obtener_password_hash(password: str) -> str:
    """Calcula el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña en texto plano contra su hash bcrypt."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def crear_token_acceso(usuario_id: uuid.UUID, rol: RolUsuario) -> str:
    """Genera un JWT firmado con claims mínimos: `sub` (id de usuario) y `rol`."""
    settings = get_settings()
    expira = datetime.now(UTC) + timedelta(minutes=settings.EXPIRACION_MINUTOS)
    payload = {"sub": str(usuario_id), "rol": rol.value, "exp": expira}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> tuple[uuid.UUID, RolUsuario]:
    """Decodifica un JWT y devuelve `(usuario_id, rol)` a partir de sus claims."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as error:
        raise TokenInvalidoError("El token es inválido o expiró.") from error
    try:
        return uuid.UUID(payload["sub"]), RolUsuario(payload["rol"])
    except (KeyError, ValueError) as error:
        raise TokenInvalidoError("El token no contiene claims válidos.") from error
