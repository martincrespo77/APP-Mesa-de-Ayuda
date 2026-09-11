"""Servicio de aplicación: casos de uso del módulo de usuarios.

Orquesta la entidad `Usuario` y el `RepositorioUsuarios` sin conocer el
motor de persistencia concreto (PyMongo o `FakeRepositorioUsuarios`).
El hashing de contraseñas ocurre en la capa de presentación/infraestructura
(`app/auth.py`, Paso 4); aquí solo se recibe el hash ya calculado.
"""

import uuid

from app.compartido.dominio import RolUsuario
from app.usuarios.dominio import Usuario
from app.usuarios.excepciones import EmailYaRegistradoError, UsuarioNoEncontradoError
from app.usuarios.repositorio import RepositorioUsuarios


class ServicioUsuarios:
    """Orquesta el registro, consulta y administración de `Usuario`."""

    def __init__(self, repositorio: RepositorioUsuarios) -> None:
        self._repositorio = repositorio

    def registrar(
        self, nombre_completo: str, email: str, password_hash: str, rol: RolUsuario
    ) -> Usuario:
        """Crea un nuevo usuario, exigiendo que el email no esté en uso."""
        if self._repositorio.buscar_por_email(email) is not None:
            raise EmailYaRegistradoError(f"El email '{email}' ya está registrado.")
        usuario = Usuario(
            nombre_completo=nombre_completo, email=email, password_hash=password_hash, rol=rol
        )
        self._repositorio.guardar(usuario)
        return usuario

    def obtener_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self._repositorio.buscar_por_id(usuario_id)

    def obtener_por_email(self, email: str) -> Usuario | None:
        return self._repositorio.buscar_por_email(email)

    def listar_todos(self) -> list[Usuario]:
        return self._repositorio.listar_todos()

    def activar(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._buscar_o_lanzar(usuario_id)
        usuario.activar()
        self._repositorio.guardar(usuario)
        return usuario

    def desactivar(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._buscar_o_lanzar(usuario_id)
        usuario.desactivar()
        self._repositorio.guardar(usuario)
        return usuario

    def cambiar_rol(self, usuario_id: uuid.UUID, nuevo_rol: RolUsuario) -> Usuario:
        usuario = self._buscar_o_lanzar(usuario_id)
        usuario.cambiar_rol(nuevo_rol)
        self._repositorio.guardar(usuario)
        return usuario

    def _buscar_o_lanzar(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._repositorio.buscar_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError(f"No existe un usuario con id '{usuario_id}'.")
        return usuario
