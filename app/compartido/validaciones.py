"""Validaciones de forma compartidas por las entidades de dominio.

Reemplazan a los `@staticmethod _validar_*` que cada entidad repetía
(título, descripción, nombre, comentario, enums...): esas validaciones no
dependen del estado de ninguna instancia, así que no son comportamiento
de la entidad sino reglas de formato reutilizables. Las reglas de negocio
(quién puede hacer qué, en qué estado) siguen viviendo en las entidades.

Un valor vacío lanza `DatoInvalidoError` (un `DominioError`, traducido a
HTTP 422); un tipo incorrecto lanza `TypeError`, porque es un error de
programación: los DTOs de Pydantic ya garantizan los tipos.
"""

from app.compartido.excepciones import DatoInvalidoError


def texto_obligatorio(valor: object, campo: str, recortar: bool = True) -> str:
    """Exige que `valor` sea texto no vacío (ni solo espacios).

    Devuelve el texto sin espacios al borde, salvo con `recortar=False`
    (ej. un hash de contraseña, que debe conservarse byte a byte).
    """
    if not isinstance(valor, str):
        raise TypeError(f"El campo '{campo}' debe ser una cadena de texto.")
    if not valor.strip():
        raise DatoInvalidoError(f"El campo '{campo}' no puede estar vacío.")
    return valor.strip() if recortar else valor


def instancia_de[T](valor: object, tipo: type[T], campo: str) -> T:
    """Devuelve `valor` exigiendo que sea instancia de `tipo` (ej. un enum de dominio)."""
    if not isinstance(valor, tipo):
        raise TypeError(f"El campo '{campo}' debe ser una instancia de {tipo.__name__}.")
    return valor
