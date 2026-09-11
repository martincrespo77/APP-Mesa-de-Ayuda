"""Jerarquía de excepciones del dominio de requerimientos."""

from app.compartido.excepciones import DominioError


class RequerimientoError(DominioError):
    """Excepción base para todos los errores del dominio de requerimientos."""


class TransicionInvalidaError(RequerimientoError):
    """Lanzada cuando se solicita un cambio de estado no permitido desde el estado actual."""


class TecnicoNoAsignadoError(RequerimientoError):
    """Lanzada al intentar iniciar progreso sin un técnico asignado previamente."""


class NotaResolucionRequeridaError(RequerimientoError):
    """Lanzada al intentar resolver un requerimiento sin una nota descriptiva."""


class PermisoDenegadoError(RequerimientoError):
    """Lanzada cuando el rol o la identidad del actor no autoriza la operación solicitada."""
