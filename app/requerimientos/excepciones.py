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


class RequerimientoNoEncontradoError(RequerimientoError):
    """Lanzada al operar sobre un id de requerimiento que no existe en el repositorio."""


class TecnicoInvalidoError(RequerimientoError):
    """Lanzada al asignar o derivar a un id que no es un Técnico activo existente.

    La lanza `Requerimiento` cuando el destino contesta que no puede recibir
    requerimientos (`usuario.puede_recibir_requerimientos()`), o el servicio
    cuando el id ni siquiera existe en el repositorio.
    """
