"""Servicio de aplicación: casos de uso del módulo de usuarios.

Solo orquesta (recibe datos ya validados → recupera/instancia entidades →
las opera → persiste → devuelve): ninguna regla de negocio vive acá. Qué
email admite cada rol, cuándo un login es válido o qué usuario puede
recibir tickets lo decide la propia jerarquía `Usuario`. El hashing de
contraseñas ocurre en infraestructura (`app/auth.py`); aquí solo se recibe
el hash ya calculado y la función de verificación inyectada.
"""

import uuid
from collections.abc import Callable

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.compartido.excepciones import DatoInvalidoError
from app.usuarios.dominio import Email, FabricaUsuarios, Usuario
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
        """Crea un nuevo usuario del rol pedido, exigiendo que el email no esté en uso.

        La unicidad del email es la única validación propia del caso de uso:
        requiere consultar al repositorio, algo que una entidad no puede
        hacer. Construir `Email` primero garantiza que el chequeo use la
        forma normalizada (la misma con la que se persiste).
        """
        email_normalizado = Email(email)
        if self._repositorio.buscar_por_email(email_normalizado) is not None:
            raise EmailYaRegistradoError(f"El email '{email_normalizado}' ya está registrado.")
        usuario = FabricaUsuarios.crear(
            rol,
            nombre_completo=nombre_completo,
            email=email,
            password_hash=password_hash,
            servicios_suscriptos=servicios_suscriptos,
        )
        self._repositorio.guardar(usuario)
        return usuario

    def autenticar(self, email: str, password: str) -> Usuario:
        """Busca al usuario y le pide que se autentique (él decide si el login es válido).

        Un email mal formado se responde igual que uno inexistente (401): el
        login no debe revelar por qué falló.
        """
        try:
            email_buscado = Email(email)
        except DatoInvalidoError:
            raise CredencialesInvalidasError("Email o contraseña incorrectos.") from None
        usuario = self._repositorio.buscar_por_email(email_buscado)
        if usuario is None:
            raise CredencialesInvalidasError("Email o contraseña incorrectos.")
        usuario.autenticar(password, self._verificador_password)
        self._repositorio.guardar(usuario)
        return usuario

    def obtener_por_id(self, usuario_id: uuid.UUID) -> Usuario | None:
        return self._repositorio.buscar_por_id(usuario_id)

    def obtener_por_email(self, email: str) -> Usuario | None:
        return self._repositorio.buscar_por_email(Email(email))

    def listar_todos(self) -> list[Usuario]:
        return self._repositorio.listar_todos()

    def listar_tecnicos_activos(self) -> list[Usuario]:
        """Usuarios a los que hoy se les puede asignar o derivar un ticket
        (para poblar los selectores de asignación/derivación)."""
        return [
            usuario
            for usuario in self._repositorio.listar_todos()
            if usuario.puede_recibir_requerimientos()
        ]

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
        """Persiste la nueva encarnación del usuario (mismo id) en el rol pedido."""
        usuario = self._buscar_o_lanzar(usuario_id)
        usuario_con_nuevo_rol = usuario.cambiar_rol(nuevo_rol)
        self._repositorio.guardar(usuario_con_nuevo_rol)
        return usuario_con_nuevo_rol

    def _buscar_o_lanzar(self, usuario_id: uuid.UUID) -> Usuario:
        usuario = self._repositorio.buscar_por_id(usuario_id)
        if usuario is None:
            raise UsuarioNoEncontradoError(f"No existe un usuario con id '{usuario_id}'.")
        return usuario
