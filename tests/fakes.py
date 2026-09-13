"""Repositorios en memoria (`FakeRepositorio*`) para tests de servicios.

Implementan los mismos contratos ABC que usará la infraestructura real con
PyMongo (Paso 5), pero con diccionarios de Python en memoria. Permiten
probar `ServicioUsuarios` y `ServicioRequerimientos` en milisegundos, sin
tocar disco ni red (doc07: capa de "Tests de Servicios" de la pirámide).
"""

import uuid

from app.notificaciones.dominio import Notificacion
from app.notificaciones.repositorio import RepositorioNotificaciones
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.repositorio import RepositorioRequerimientos
from app.supervision.dominio import RelacionSupervision
from app.supervision.repositorio import RepositorioSupervision
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


class FakeRepositorioSupervision(RepositorioSupervision):
    """Implementación en memoria de `RepositorioSupervision`, solo para tests."""

    def __init__(self) -> None:
        self._relaciones: dict[uuid.UUID, RelacionSupervision] = {}

    def asignar(self, relacion: RelacionSupervision) -> None:
        self._relaciones[relacion.id] = relacion

    def remover(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> None:
        for relacion_id, relacion in list(self._relaciones.items()):
            coincide = (
                relacion.supervisor_id == supervisor_id
                and relacion.supervisado_id == supervisado_id
            )
            if coincide:
                del self._relaciones[relacion_id]

    def existe(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> bool:
        return any(
            r.supervisor_id == supervisor_id and r.supervisado_id == supervisado_id
            for r in self._relaciones.values()
        )

    def listar_supervisados_de(self, supervisor_id: uuid.UUID) -> list[RelacionSupervision]:
        return [r for r in self._relaciones.values() if r.supervisor_id == supervisor_id]

    def listar_supervisores_de(self, supervisado_id: uuid.UUID) -> list[RelacionSupervision]:
        return [r for r in self._relaciones.values() if r.supervisado_id == supervisado_id]


class FakeRepositorioNotificaciones(RepositorioNotificaciones):
    """Implementación en memoria de `RepositorioNotificaciones`, solo para tests."""

    def __init__(self) -> None:
        self._notificaciones: dict[uuid.UUID, Notificacion] = {}

    def guardar(self, notificacion: Notificacion) -> None:
        self._notificaciones[notificacion.id] = notificacion

    def buscar_por_id(self, notificacion_id: uuid.UUID) -> Notificacion | None:
        return self._notificaciones.get(notificacion_id)

    def listar_por_supervisor(self, supervisor_id: uuid.UUID) -> list[Notificacion]:
        return [n for n in self._notificaciones.values() if n.supervisor_id == supervisor_id]
