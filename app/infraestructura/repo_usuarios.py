"""Adaptador PyMongo de `RepositorioUsuarios` (Paso 5).

Traduce entre `Usuario` (dominio puro) y documentos BSON de la colección
`usuarios`. El id de dominio (UUID) se guarda como `_id` de Mongo en
formato string (ver `app/infraestructura/database.py`); el dominio nunca
ve ese `_id`, solo su propio `usuario.id`.

`Usuario.__init__` no tiene efectos colaterales (a diferencia de
`Requerimiento`, que registra un evento `CREACION`), así que reconstruir
una instancia desde un documento reutiliza el constructor normal sin
necesidad de un método de reconstrucción dedicado.
"""

import uuid
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.infraestructura.database import COLECCION_USUARIOS
from app.usuarios.dominio import Usuario
from app.usuarios.repositorio import RepositorioUsuarios


class RepositorioUsuariosMongo(RepositorioUsuarios):
    """Implementación con PyMongo del contrato `RepositorioUsuarios`."""

    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._coleccion: Collection[dict[str, Any]] = db[COLECCION_USUARIOS]

    def guardar(self, usuario: Usuario) -> None:
        documento = _a_documento(usuario)
        self._coleccion.replace_one({"_id": documento["_id"]}, documento, upsert=True)

    def buscar_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        documento = self._coleccion.find_one({"_id": str(usuario_id)})
        return _a_dominio(documento) if documento is not None else None

    def buscar_por_email(self, email: str) -> Usuario | None:
        documento = self._coleccion.find_one({"email": email})
        return _a_dominio(documento) if documento is not None else None

    def listar_todos(self) -> list[Usuario]:
        return [_a_dominio(documento) for documento in self._coleccion.find()]


def _a_documento(usuario: Usuario) -> dict[str, Any]:
    """Serializa un `Usuario` al documento BSON que se persiste en Mongo."""
    return {
        "_id": str(usuario.id),
        "nombre_completo": usuario.nombre_completo,
        "email": usuario.email,
        "password_hash": usuario.password_hash,
        "rol": usuario.rol.value,
        "activo": usuario.activo,
        "servicios_suscriptos": [servicio.value for servicio in usuario.servicios_suscriptos],
        "fecha_creacion": usuario.fecha_creacion,
        "ultimo_acceso": usuario.ultimo_acceso,
    }


def _a_dominio(documento: dict[str, Any]) -> Usuario:
    """Reconstruye un `Usuario` a partir del documento BSON leído de Mongo."""
    return Usuario(
        id=uuid.UUID(documento["_id"]),
        nombre_completo=documento["nombre_completo"],
        email=documento["email"],
        password_hash=documento["password_hash"],
        rol=RolUsuario(documento["rol"]),
        activo=documento["activo"],
        servicios_suscriptos=frozenset(
            ServicioComunicarlos(s) for s in documento.get("servicios_suscriptos", [])
        ),
        fecha_creacion=documento["fecha_creacion"],
        ultimo_acceso=documento.get("ultimo_acceso"),
    )
