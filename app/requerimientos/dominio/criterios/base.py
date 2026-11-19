"""Clase abstracta `CriterioVisibilidad`: Specification pura de qué tickets ve un actor.

Reemplaza a `Usuario.requerimientos_visibles(repositorio)`, que acoplaba la
entidad de dominio con el puerto de persistencia. Ahora cada rol devuelve
su criterio (`actor.criterio_visibilidad()`), el servicio se lo entrega al
repositorio y el repositorio lo ejecuta:

- en memoria, con `es_satisfecho_por(requerimiento)`;
- en una base de datos, con `traducir(traductor)` (double dispatch hacia el
  `TraductorCriterios` del adaptador, sin `isinstance`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.dominio.criterios.traductor import TraductorCriterios


class CriterioVisibilidad(ABC):
    """Especificación de visibilidad; no conoce MongoDB ni SQL."""

    @abstractmethod
    def es_satisfecho_por(self, requerimiento: Requerimiento) -> bool:
        """¿`requerimiento` cumple este criterio?"""

    @abstractmethod
    def traducir[T](self, traductor: TraductorCriterios[T]) -> T:
        """Pide al traductor de infraestructura la consulta equivalente a este criterio."""
