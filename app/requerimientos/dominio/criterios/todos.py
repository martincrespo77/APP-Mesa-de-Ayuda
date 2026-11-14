"""Criterio `CriterioTodos`: la bandeja completa (visibilidad de todo empleado)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.requerimientos.dominio.criterios.base import CriterioVisibilidad

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.dominio.criterios.traductor import TraductorCriterios


@dataclass(frozen=True)
class CriterioTodos(CriterioVisibilidad):
    """Todo requerimiento satisface este criterio."""

    def es_satisfecho_por(self, requerimiento: Requerimiento) -> bool:
        return True

    def traducir[T](self, traductor: TraductorCriterios[T]) -> T:
        return traductor.todos()
