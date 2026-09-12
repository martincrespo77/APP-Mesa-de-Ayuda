"""Entidad de dominio `Usuario`.

Modela a las personas que interactúan con la Mesa de Ayuda (solicitantes,
operadores, técnicos y supervisores). El hashing real de contraseñas
(`bcrypt`) y la emisión de tokens JWT son responsabilidad de la capa de
infraestructura/presentación (`app/auth.py`, Paso 4); esta entidad solo
garantiza que nunca exista un `Usuario` con datos incompletos o en un
estado de contraseña/actividad inválido.
"""

import re
import uuid

from app.compartido.dominio import RolUsuario
from app.usuarios.excepciones import (
    EmailCorporativoRequeridoError,
    UsuarioYaActivoError,
    UsuarioYaInactivoError,
)

_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_DOMINIO_CORPORATIVO = "comunicarlos.com.ar"
_ROLES_CON_EMAIL_CORPORATIVO = frozenset(
    {RolUsuario.OPERADOR, RolUsuario.TECNICO, RolUsuario.SUPERVISOR}
)


class Usuario:
    """Persona registrada en el sistema, con un rol de negocio y un estado."""

    def __init__(
        self,
        nombre_completo: str,
        email: str,
        password_hash: str,
        rol: RolUsuario,
        id: uuid.UUID | None = None,
        activo: bool = True,
    ) -> None:
        self.id = id or uuid.uuid4()
        self.nombre_completo = self._validar_nombre_completo(nombre_completo)
        self._rol = self._validar_rol(rol)
        self.email = self._validar_email(email, self._rol)
        self._password_hash = self._validar_password_hash(password_hash)
        self._activo = activo

    @property
    def password_hash(self) -> str:
        return self._password_hash

    @property
    def rol(self) -> RolUsuario:
        return self._rol

    @property
    def activo(self) -> bool:
        return self._activo

    def activar(self) -> None:
        """Reactiva a un usuario previamente desactivado."""
        if self._activo:
            raise UsuarioYaActivoError(f"El usuario '{self.email}' ya está activo.")
        self._activo = True

    def desactivar(self) -> None:
        """Da de baja lógica a un usuario (ej. egreso de la cooperativa)."""
        if not self._activo:
            raise UsuarioYaInactivoError(f"El usuario '{self.email}' ya está inactivo.")
        self._activo = False

    def cambiar_rol(self, nuevo_rol: RolUsuario) -> None:
        """Reasigna el rol de negocio del usuario.

        Si el nuevo rol es Operador/Técnico/Supervisor, exige que el email
        ya registrado cumpla el dominio corporativo (no se puede ascender a
        un rol operativo con un email personal).
        """
        nuevo_rol_validado = self._validar_rol(nuevo_rol)
        self._validar_dominio_corporativo(self.email, nuevo_rol_validado)
        self._rol = nuevo_rol_validado

    def cambiar_password_hash(self, nuevo_password_hash: str) -> None:
        """Reemplaza el hash de contraseña por uno nuevo ya calculado en infraestructura."""
        self._password_hash = self._validar_password_hash(nuevo_password_hash)

    @staticmethod
    def _validar_nombre_completo(nombre_completo: str) -> str:
        if not isinstance(nombre_completo, str):
            raise TypeError("El nombre completo debe ser una cadena de texto.")
        nombre_normalizado = nombre_completo.strip()
        if not nombre_normalizado:
            raise ValueError("El nombre completo no puede estar vacío.")
        return nombre_normalizado

    @staticmethod
    def _validar_email(email: str, rol: RolUsuario) -> str:
        if not isinstance(email, str):
            raise TypeError("El email debe ser una cadena de texto.")
        email_normalizado = email.strip().lower()
        if not _PATRON_EMAIL.match(email_normalizado):
            raise ValueError(f"El email '{email}' no tiene un formato válido.")
        Usuario._validar_dominio_corporativo(email_normalizado, rol)
        return email_normalizado

    @staticmethod
    def _validar_dominio_corporativo(email_normalizado: str, rol: RolUsuario) -> None:
        """Operador, Técnico y Supervisor requieren email `@comunicarlos.com.ar`.

        El Solicitante puede usar cualquier email (regla de negocio: "Los
        solicitantes utilizarán cualquier correo electrónico").
        """
        if rol not in _ROLES_CON_EMAIL_CORPORATIVO:
            return
        if not email_normalizado.endswith(f"@{_DOMINIO_CORPORATIVO}"):
            raise EmailCorporativoRequeridoError(
                f"El rol '{rol}' requiere un email corporativo "
                f"'@{_DOMINIO_CORPORATIVO}' (recibido: '{email_normalizado}')."
            )

    @staticmethod
    def _validar_password_hash(password_hash: str) -> str:
        if not isinstance(password_hash, str):
            raise TypeError("El hash de contraseña debe ser una cadena de texto.")
        if not password_hash.strip():
            raise ValueError("El hash de contraseña no puede estar vacío.")
        return password_hash

    @staticmethod
    def _validar_rol(rol: RolUsuario) -> RolUsuario:
        if not isinstance(rol, RolUsuario):
            raise TypeError("El rol debe ser una instancia de RolUsuario.")
        return rol
