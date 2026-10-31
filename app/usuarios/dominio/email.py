"""Value Object `Email`: dirección de correo normalizada y validada.

El email es la identidad de login y es case-insensitive por convención:
`Lucia.Gomez@...` y `lucia.gomez@...` son la MISMA persona. Antes la
normalización era un `@staticmethod` público de `Usuario` que el servicio
tenía que acordarse de llamar antes de consultar el repositorio; como Value
Object, un `Email` siempre está normalizado desde su construcción, y
cualquier búsqueda por email recibe un `Email` (no un `str` crudo), así que
es imposible olvidarse de normalizar.
"""

import re

from app.compartido.excepciones import DatoInvalidoError

_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Email:
    """Dirección de email inmutable, en su forma canónica (sin espacios, minúsculas)."""

    __slots__ = ("_valor",)

    def __init__(self, valor: str) -> None:
        if not isinstance(valor, str):
            raise TypeError("El email debe ser una cadena de texto.")
        normalizado = valor.strip().lower()
        if not _PATRON_EMAIL.match(normalizado):
            raise DatoInvalidoError(f"El email '{valor}' no tiene un formato válido.")
        self._valor = normalizado

    def pertenece_al_dominio(self, dominio: str) -> bool:
        """¿La dirección es de `dominio` (ej. el dominio corporativo de la cooperativa)?"""
        return self._valor.endswith(f"@{dominio}")

    def __str__(self) -> str:
        return self._valor

    def __repr__(self) -> str:
        return f"Email({self._valor!r})"

    def __eq__(self, otro: object) -> bool:
        return isinstance(otro, Email) and self._valor == otro._valor

    def __hash__(self) -> int:
        return hash(self._valor)
