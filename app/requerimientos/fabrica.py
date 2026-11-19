"""Factory Method: reconstrucción polimórfica de `Requerimiento` desde persistencia.

Desacopla a los repositorios de las clases concretas `Incidente` y
`Solicitud`. La CREACIÓN de requerimientos nuevos ya no pasa por acá con
`**atributos`: cada tipo tiene su Value Object de creación
(`DatosIncidente` / `DatosSolicitud`), que construye la entidad concreta
para el `Usuario` solicitante. Para incorporar un nuevo tipo basta crear su
entidad y sus datos de creación, y registrarlo aquí con `registrar_tipo`.
"""

from typing import Any

from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.codigos import TipoRequerimiento
from app.requerimientos.dominio.incidente import Incidente
from app.requerimientos.dominio.solicitud import Solicitud


class FabricaRequerimientos:
    """Fábrica que centraliza la reconstrucción de instancias de `Requerimiento`."""

    _catalogo: dict[TipoRequerimiento, type[Requerimiento]] = {
        TipoRequerimiento.INCIDENTE: Incidente,
        TipoRequerimiento.SOLICITUD: Solicitud,
    }

    @classmethod
    def reconstruir(cls, tipo: TipoRequerimiento, **atributos: Any) -> Requerimiento:
        """Reconstruye el `Requerimiento` concreto correspondiente al `tipo` dado.

        Uso exclusivo de los repositorios concretos de persistencia: delega
        en el `reconstruir(**atributos)` de la clase concreta, que no dispara
        el evento `CREACION` del constructor normal.
        """
        clase_requerimiento = cls._catalogo.get(tipo)
        if clase_requerimiento is None:
            tipos_validos = ", ".join(t.value for t in cls._catalogo)
            raise ValueError(f"Tipo '{tipo}' no soportado. Disponibles: {tipos_validos}")
        return clase_requerimiento.reconstruir(**atributos)  # type: ignore[attr-defined,no-any-return]

    @classmethod
    def registrar_tipo(
        cls, tipo: TipoRequerimiento, clase_requerimiento: type[Requerimiento]
    ) -> None:
        """Permite extender la fábrica dinámicamente sin modificar su código base."""
        cls._catalogo[tipo] = clase_requerimiento
