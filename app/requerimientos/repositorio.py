"""Puerto de persistencia del dominio de requerimientos (Dependency Inversion).

`Requerimiento` es la abstracción retornada: la implementación concreta
(PyMongo en Paso 5, o `FakeRepositorioRequerimientos` en tests) decide cómo
reconstruir un `Incidente` o una `Solicitud` a partir de los datos crudos,
sin que los servicios de aplicación conozcan ese detalle.
"""

import uuid
from abc import ABC, abstractmethod

from app.requerimientos.dominio.base import Requerimiento


class RepositorioRequerimientos(ABC):
    """Contrato de persistencia para la jerarquía `Requerimiento`."""

    @abstractmethod
    def guardar(self, requerimiento: Requerimiento) -> None:
        """Inserta o actualiza el requerimiento (upsert por `requerimiento.id`)."""

    @abstractmethod
    def buscar_por_id(self, requerimiento_id: uuid.UUID) -> Requerimiento | None:
        """Devuelve el requerimiento con ese id, o `None` si no existe."""

    @abstractmethod
    def listar_todos(self) -> list[Requerimiento]:
        """Devuelve todos los requerimientos (visibilidad de Operador/Técnico/Supervisor)."""

    @abstractmethod
    def listar_por_solicitante(self, solicitante_id: uuid.UUID) -> list[Requerimiento]:
        """Devuelve solo los requerimientos creados por ese solicitante (visibilidad propia)."""
