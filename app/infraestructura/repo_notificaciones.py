"""Adaptador PyMongo de `RepositorioNotificaciones` (mismo patrón que
`repo_usuarios.py`: `_id` = UUID en formato string, `replace_one` upsert).
"""

import uuid
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.infraestructura.database import COLECCION_NOTIFICACIONES
from app.notificaciones.dominio import Notificacion
from app.notificaciones.repositorio import RepositorioNotificaciones
from app.requerimientos.eventos import TipoEventoRequerimiento


class RepositorioNotificacionesMongo(RepositorioNotificaciones):
    """Implementación con PyMongo del contrato `RepositorioNotificaciones`."""

    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._coleccion: Collection[dict[str, Any]] = db[COLECCION_NOTIFICACIONES]

    def guardar(self, notificacion: Notificacion) -> None:
        documento = _a_documento(notificacion)
        self._coleccion.replace_one({"_id": documento["_id"]}, documento, upsert=True)

    def buscar_por_id(self, notificacion_id: uuid.UUID) -> Notificacion | None:
        documento = self._coleccion.find_one({"_id": str(notificacion_id)})
        return _a_dominio(documento) if documento is not None else None

    def listar_por_supervisor(self, supervisor_id: uuid.UUID) -> list[Notificacion]:
        filtro = {"supervisor_id": str(supervisor_id)}
        return [_a_dominio(documento) for documento in self._coleccion.find(filtro)]


def _a_documento(notificacion: Notificacion) -> dict[str, Any]:
    return {
        "_id": str(notificacion.id),
        "supervisor_id": str(notificacion.supervisor_id),
        "empleado_supervisado_id": str(notificacion.empleado_supervisado_id),
        "requerimiento_id": str(notificacion.requerimiento_id),
        "tipo_evento": notificacion.tipo_evento.value,
        "detalle": notificacion.detalle,
        "timestamp": notificacion.timestamp,
        "leida": notificacion.leida,
    }


def _a_dominio(documento: dict[str, Any]) -> Notificacion:
    return Notificacion(
        id=uuid.UUID(documento["_id"]),
        supervisor_id=uuid.UUID(documento["supervisor_id"]),
        empleado_supervisado_id=uuid.UUID(documento["empleado_supervisado_id"]),
        requerimiento_id=uuid.UUID(documento["requerimiento_id"]),
        tipo_evento=TipoEventoRequerimiento(documento["tipo_evento"]),
        detalle=documento["detalle"],
        timestamp=documento["timestamp"],
        leida=documento["leida"],
    )
