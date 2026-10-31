"""Shared Kernel: raíz de la jerarquía de excepciones de dominio.

Todas las excepciones de negocio del sistema (`usuarios`, `requerimientos`,
etc.) heredan de `DominioError`, de modo que la capa de presentación pueda
capturarlas de forma genérica en un único manejador de errores de FastAPI.
"""


class DominioError(Exception):
    """Excepción base para toda violación de una regla de negocio del sistema."""


class DatoInvalidoError(DominioError, ValueError):
    """Lanzada cuando un dato no cumple el formato que exige el dominio
    (texto obligatorio vacío, email mal formado...).

    Hereda de `DominioError` para que el exception handler la traduzca a una
    respuesta HTTP (en vez de un 500), y de `ValueError` porque semánticamente
    es un valor inválido.
    """
