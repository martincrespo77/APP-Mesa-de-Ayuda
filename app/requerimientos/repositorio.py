"""Puerto de persistencia del dominio de requerimientos (Dependency Inversion).

`Requerimiento` es la abstracción retornada: la implementación concreta
(PyMongo, o `FakeRepositorioRequerimientos` en tests) decide cómo
reconstruir un `Incidente` o una `Solicitud` a partir de los datos crudos,
sin que los servicios de aplicación conozcan ese detalle.

La visibilidad por actor no es un método por rol (`listar_por_solicitante`,
...): el repositorio ejecuta el `CriterioVisibilidad` que le devuelve el
propio actor (Patrón Specification).
"""

import uuid
from abc import ABC, abstractmethod

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.criterios.base import CriterioVisibilidad


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
        """Devuelve todos los requerimientos, sin restricción de visibilidad."""

    @abstractmethod
    def listar_por_criterio(self, criterio: CriterioVisibilidad) -> list[Requerimiento]:
        """Devuelve los requerimientos que satisfacen `criterio`."""
