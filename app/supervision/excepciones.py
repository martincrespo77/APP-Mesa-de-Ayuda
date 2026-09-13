"""Jerarquía de excepciones del dominio de supervisión."""

from app.compartido.excepciones import DominioError


class SupervisionError(DominioError):
    """Excepción base para todos los errores del dominio de supervisión."""


class RelacionInvalidaError(SupervisionError):
    """Lanzada al intentar crear una relación inconsistente (ej. autosupervisión)."""


class RelacionYaExisteError(SupervisionError):
    """Lanzada al asignar una relación supervisor/supervisado ya existente."""


class RolNoSupervisableError(SupervisionError):
    """Lanzada cuando el supervisado no tiene un rol supervisable (Operador/Técnico)."""
