"""Factory Method: creación polimórfica de `Requerimiento`.

Desacopla al código cliente (servicios de aplicación, Paso 3) de las clases
concretas `Incidente` y `Solicitud`. Para incorporar un nuevo tipo de
requerimiento basta crear su archivo en `dominio/` y registrarlo aquí con
`registrar_tipo`, sin modificar el resto del sistema (Open/Closed).
"""

from typing import Any

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import TipoRequerimiento
from app.requerimientos.dominio.incidente import Incidente
from app.requerimientos.dominio.solicitud import Solicitud


class FabricaRequerimientos:
    """Fábrica que centraliza la creación de instancias de `Requerimiento`."""

    _catalogo: dict[TipoRequerimiento, type[Requerimiento]] = {
        TipoRequerimiento.INCIDENTE: Incidente,
        TipoRequerimiento.SOLICITUD: Solicitud,
    }

    @classmethod
    def crear(cls, tipo: TipoRequerimiento, **atributos: Any) -> Requerimiento:
        """Instancia el `Requerimiento` concreto correspondiente al `tipo` dado.

        `atributos` se pasan tal cual al constructor de la clase concreta
        (cada tipo exige sus propios campos: `severidad` para `Incidente`,
        `categoria`/`fecha_limite` para `Solicitud`, etc.).
        """
        clase_requerimiento = cls._catalogo.get(tipo)
        if clase_requerimiento is None:
            tipos_validos = ", ".join(t.value for t in cls._catalogo)
            raise ValueError(f"Tipo '{tipo}' no soportado. Disponibles: {tipos_validos}")
        return clase_requerimiento(**atributos)

    @classmethod
    def registrar_tipo(
        cls, tipo: TipoRequerimiento, clase_requerimiento: type[Requerimiento]
    ) -> None:
        """Permite extender la fábrica dinámicamente sin modificar su código base."""
        cls._catalogo[tipo] = clase_requerimiento
