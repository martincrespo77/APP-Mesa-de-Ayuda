"""Puerto de persistencia del dominio de notificaciones (Dependency Inversion)."""

import uuid
from abc import ABC, abstractmethod

from app.notificaciones.dominio import Notificacion


class RepositorioNotificaciones(ABC):
    """Contrato de persistencia para la entidad `Notificacion`."""

    @abstractmethod
    def guardar(self, notificacion: Notificacion) -> None:
        """Inserta o actualiza la notificación (upsert por `notificacion.id`)."""

    @abstractmethod
    def buscar_por_id(self, notificacion_id: uuid.UUID) -> Notificacion | None:
        """Devuelve la notificación con ese id, o `None` si no existe."""

    @abstractmethod
    def listar_por_supervisor(self, supervisor_id: uuid.UUID) -> list[Notificacion]:
        """Devuelve todas las notificaciones destinadas a ese supervisor."""
