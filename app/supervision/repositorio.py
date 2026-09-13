"""Puerto de persistencia del dominio de supervisión (Dependency Inversion)."""

import uuid
from abc import ABC, abstractmethod

from app.supervision.dominio import RelacionSupervision


class RepositorioSupervision(ABC):
    """Contrato de persistencia para `RelacionSupervision`."""

    @abstractmethod
    def asignar(self, relacion: RelacionSupervision) -> None:
        """Persiste una nueva relación de supervisión."""

    @abstractmethod
    def remover(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> None:
        """Elimina la relación entre ese supervisor y supervisado, si existía."""

    @abstractmethod
    def existe(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> bool:
        """Indica si ya existe esa relación exacta (evita duplicados)."""

    @abstractmethod
    def listar_supervisados_de(self, supervisor_id: uuid.UUID) -> list[RelacionSupervision]:
        """Todas las relaciones donde ese usuario es el supervisor."""

    @abstractmethod
    def listar_supervisores_de(self, supervisado_id: uuid.UUID) -> list[RelacionSupervision]:
        """Todas las relaciones donde ese usuario es el supervisado."""
