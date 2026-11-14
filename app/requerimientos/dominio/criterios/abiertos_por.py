"""Criterio `CriterioAbiertosPor`: solo los tickets que abrió un solicitante."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.requerimientos.dominio.criterios.base import CriterioVisibilidad

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.dominio.criterios.traductor import TraductorCriterios
    from app.usuarios.dominio import Usuario


@dataclass(frozen=True)
class CriterioAbiertosPor(CriterioVisibilidad):
    """Requerimientos que pertenecen a `solicitante` (le pregunta al ticket, no compara ids)."""

    solicitante: Usuario

    def es_satisfecho_por(self, requerimiento: Requerimiento) -> bool:
        return requerimiento.pertenece_a(self.solicitante)

    def traducir[T](self, traductor: TraductorCriterios[T]) -> T:
        return traductor.abiertos_por(self.solicitante)
