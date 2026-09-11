"""Jerarquía de excepciones del dominio de usuarios."""

from app.compartido.excepciones import DominioError


class UsuarioError(DominioError):
    """Excepción base para todos los errores del dominio de usuarios."""


class UsuarioYaActivoError(UsuarioError):
    """Lanzada al intentar activar un usuario que ya se encuentra activo."""


class UsuarioYaInactivoError(UsuarioError):
    """Lanzada al intentar desactivar un usuario que ya se encuentra inactivo."""
