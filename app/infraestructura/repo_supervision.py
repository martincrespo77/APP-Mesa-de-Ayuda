"""Adaptador PyMongo de `RepositorioSupervision` (mismo patrón que
`repo_usuarios.py`: `_id` = UUID en formato string, `replace_one` upsert).
"""

import uuid
from typing import Any

from pymongo.collection import Collection
from pymongo.database import Database

from app.infraestructura.database import COLECCION_SUPERVISIONES
from app.supervision.dominio import RelacionSupervision
from app.supervision.repositorio import RepositorioSupervision


class RepositorioSupervisionMongo(RepositorioSupervision):
    """Implementación con PyMongo del contrato `RepositorioSupervision`."""

    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._coleccion: Collection[dict[str, Any]] = db[COLECCION_SUPERVISIONES]

    def asignar(self, relacion: RelacionSupervision) -> None:
        documento = _a_documento(relacion)
        self._coleccion.replace_one({"_id": documento["_id"]}, documento, upsert=True)

    def remover(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> None:
        self._coleccion.delete_one(
            {"supervisor_id": str(supervisor_id), "supervisado_id": str(supervisado_id)}
        )

    def existe(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> bool:
        documento = self._coleccion.find_one(
            {"supervisor_id": str(supervisor_id), "supervisado_id": str(supervisado_id)}
        )
        return documento is not None

    def listar_supervisados_de(self, supervisor_id: uuid.UUID) -> list[RelacionSupervision]:
        filtro = {"supervisor_id": str(supervisor_id)}
        return [_a_dominio(documento) for documento in self._coleccion.find(filtro)]

    def listar_supervisores_de(self, supervisado_id: uuid.UUID) -> list[RelacionSupervision]:
        filtro = {"supervisado_id": str(supervisado_id)}
        return [_a_dominio(documento) for documento in self._coleccion.find(filtro)]


def _a_documento(relacion: RelacionSupervision) -> dict[str, Any]:
    return {
        "_id": str(relacion.id),
        "supervisor_id": str(relacion.supervisor_id),
        "supervisado_id": str(relacion.supervisado_id),
        "fecha_asignacion": relacion.fecha_asignacion,
    }


def _a_dominio(documento: dict[str, Any]) -> RelacionSupervision:
    return RelacionSupervision(
        id=uuid.UUID(documento["_id"]),
        supervisor_id=uuid.UUID(documento["supervisor_id"]),
        supervisado_id=uuid.UUID(documento["supervisado_id"]),
        fecha_asignacion=documento["fecha_asignacion"],
    )
