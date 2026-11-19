"""Patrón Specification: criterios de visibilidad de requerimientos por actor."""

from app.requerimientos.dominio.criterios.abiertos_por import CriterioAbiertosPor
from app.requerimientos.dominio.criterios.base import CriterioVisibilidad
from app.requerimientos.dominio.criterios.todos import CriterioTodos
from app.requerimientos.dominio.criterios.traductor import TraductorCriterios

__all__ = [
    "CriterioAbiertosPor",
    "CriterioTodos",
    "CriterioVisibilidad",
    "TraductorCriterios",
]
