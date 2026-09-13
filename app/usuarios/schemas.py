"""Esquemas Pydantic v2 (DTOs) del módulo de usuarios: requests y responses."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.compartido.dominio import RolUsuario, ServicioComunicarlos


class UsuarioCreateRequest(BaseModel):
    """Datos para que un Supervisor cree una cuenta de usuario."""

    nombre_completo: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=8)
    rol: RolUsuario
    servicios_suscriptos: list[ServicioComunicarlos] = Field(default_factory=list)


class CambiarRolRequest(BaseModel):
    """Nuevo rol a asignar a un usuario existente."""

    nuevo_rol: RolUsuario


class UsuarioResponse(BaseModel):
    """Representación pública de un `Usuario` (nunca incluye `password_hash`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre_completo: str
    email: str
    rol: RolUsuario
    activo: bool
    servicios_suscriptos: frozenset[ServicioComunicarlos]
    fecha_creacion: datetime
    ultimo_acceso: datetime | None


class TokenResponse(BaseModel):
    """Respuesta del endpoint de login."""

    access_token: str
    token_type: str = "bearer"
