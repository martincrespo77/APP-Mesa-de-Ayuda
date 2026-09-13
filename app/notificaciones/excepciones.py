"""Jerarquía de excepciones del dominio de notificaciones."""

from app.compartido.excepciones import DominioError


class NotificacionError(DominioError):
    """Excepción base para todos los errores del dominio de notificaciones."""


class NotificacionNoEncontradaError(NotificacionError):
    """Lanzada al operar sobre una notificación inexistente o ajena al supervisor."""
