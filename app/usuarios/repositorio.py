"""Puerto de persistencia del dominio de usuarios (Dependency Inversion).

Los servicios de aplicación dependen únicamente de esta interfaz abstracta,
nunca de un driver concreto. La implementación con PyMongo (Paso 5) y la
implementación en memoria para tests (`FakeRepositorioUsuarios`) satisfacen
el mismo contrato.
"""

import uuid
from abc import ABC, abstractmethod

from app.usuarios.dominio import Usuario


class RepositorioUsuarios(ABC):
    """Contrato de persistencia para la entidad `Usuario`."""

    @abstractmethod
    def guardar(self, usuario: Usuario) -> None:
        """Inserta o actualiza el usuario (upsert por `usuario.id`)."""

    @abstractmethod
    def buscar_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        """Devuelve el usuario con ese id, o `None` si no existe."""

    @abstractmethod
    def buscar_por_email(self, email: str) -> Usuario | None:
        """Devuelve el usuario con ese email (login), o `None` si no existe."""

    @abstractmethod
    def listar_todos(self) -> list[Usuario]:
        """Devuelve todos los usuarios registrados."""
