"""Servicio de aplicación: casos de uso del módulo de usuarios.

Orquesta la entidad `Usuario` y el `RepositorioUsuarios` sin conocer el
motor de persistencia concreto (PyMongo o `FakeRepositorioUsuarios`).
El hashing de contraseñas ocurre en la capa de presentación/infraestructura
(`app/auth.py`, Paso 4); aquí solo se recibe el hash ya calculado.
"""

import uuid
from collections.abc import Callable

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.usuarios.dominio import Usuario
from app.usuarios.excepciones import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    UsuarioNoEncontradoError,
)
from app.usuarios.repositorio import RepositorioUsuarios


class ServicioUsuarios:
    """Orquesta el registro, consulta y administración de `Usuario`."""

    def __init__(
        self, repositorio: RepositorioUsuarios, verificador_password: Callable[[str, str], bool]
    ) -> None:
        self._repositorio = repositorio
        self._verificador_password = verificador_password

    def registrar(
        self,
        nombre_completo: str,
        email: str,
        password_hash: str,
        rol: RolUsuario,
        servicios_suscriptos: frozenset[ServicioComunicarlos] | None = None,
    ) -> Usuario:
        """Crea un nuevo usuario, exigiendo que el email no esté en uso."""
        if self._repositorio.buscar_por_email(email) is not None:
            raise EmailYaRegistradoError(f"El email '{email}' ya está registrado.")
        usuario = Usuario(
            nombre_completo=nombre_completo,
            email=email,
            password_hash=password_hash,
            rol=rol,
            servicios_suscriptos=servicios_suscriptos,
        )
        self._repositorio.guardar(usuario)
        return usuario

    def autenticar(self, email: str, password: str) -> Usuario:
        """Verifica credenciales y registra el acceso exitoso (auditoría de cuenta).

        El hashing/verificación de contraseña es responsabilidad de infraestructura
        (`app/auth.py`); el servicio recibe la función de verificación por inyección
        para no importar `bcrypt` desde la capa de dominio/aplicación.
        """
        usuario = self._repositorio.buscar_por_email(email)
        credenciales_validas = usuario is not None and self._verificador_password(
            password, usuario.password_hash
        )
        if not credenciales_validas or usuario is None or not usuario.activo:
            raise CredencialesInvalidasError("Email o contraseña incorrectos.")
        usuario.registrar_acceso()
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
