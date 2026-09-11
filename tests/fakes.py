"""Repositorios en memoria (`FakeRepositorio*`) para tests de servicios.

Implementan los mismos contratos ABC que usará la infraestructura real con
PyMongo (Paso 5), pero con diccionarios de Python en memoria. Permiten
probar `ServicioUsuarios` y `ServicioRequerimientos` en milisegundos, sin
tocar disco ni red (doc07: capa de "Tests de Servicios" de la pirámide).
"""

import uuid

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.repositorio import RepositorioRequerimientos
from app.usuarios.dominio import Usuario
from app.usuarios.repositorio import RepositorioUsuarios


class FakeRepositorioUsuarios(RepositorioUsuarios):
    """Implementación en memoria de `RepositorioUsuarios`, solo para tests."""

    def __init__(self) -> None:
        self._usuarios: dict[uuid.UUID, Usuario] = {}

    def guardar(self, usuario: Usuario) -> None:
        self._usuarios[usuario.id] = usuario

    def buscar_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self._usuarios.get(usuario_id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        for usuario in self._usuarios.values():
            if usuario.email == email:
                return usuario
        return None

    def listar_todos(self) -> list[Usuario]:
        return list(self._usuarios.values())


class FakeRepositorioRequerimientos(RepositorioRequerimientos):
    """Implementación en memoria de `RepositorioRequerimientos`, solo para tests."""

    def __init__(self) -> None:
        self._requerimientos: dict[uuid.UUID, Requerimiento] = {}

    def guardar(self, requerimiento: Requerimiento) -> None:
        self._requerimientos[requerimiento.id] = requerimiento

    def buscar_por_id(self, requerimiento_id: uuid.UUID) -> Requerimiento | None:
        return self._requerimientos.get(requerimiento_id)

    def listar_todos(self) -> list[Requerimiento]:
        return list(self._requerimientos.values())

    def listar_por_solicitante(self, solicitante_id: uuid.UUID) -> list[Requerimiento]:
        return [
            req for req in self._requerimientos.values() if req.solicitante_id == solicitante_id
        ]
