"""Shared Kernel: raíz de la jerarquía de excepciones de dominio.

Todas las excepciones de negocio del sistema (`usuarios`, `requerimientos`,
etc.) heredan de `DominioError`, de modo que la capa de presentación pueda
capturarlas de forma genérica en un único manejador de errores de FastAPI.
"""


class DominioError(Exception):
    """Excepción base para toda violación de una regla de negocio del sistema."""
