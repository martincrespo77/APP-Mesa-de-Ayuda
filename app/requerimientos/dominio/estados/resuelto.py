"""Estado `RESUELTO`: el técnico dio una solución; espera la conformidad."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.cerrado import EstadoCerrado

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.usuarios.dominio import Usuario


class EstadoResuelto(EstadoTicket):
    """RESUELTO -> CERRADO (conformidad) | EN_PROGRESO (reapertura por comentario)."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.RESUELTO

    def cerrar(self) -> EstadoTicket:
        return EstadoCerrado()

    def reabrir(self) -> EstadoTicket:
        # Import diferido: EN_PROGRESO -> RESUELTO -> EN_PROGRESO es un ciclo.
        from app.requerimientos.dominio.estados.en_progreso import EstadoEnProgreso

        return EstadoEnProgreso()

    def al_recibir_comentario(self, requerimiento: Requerimiento, actor: Usuario) -> None:
        """Un comentario de quien puede reabrir este ticket lo devuelve a EN_PROGRESO.

        Usa la misma capacidad que exige `Requerimiento.reabrir`, así ambas
        comprobaciones no pueden discrepar a mitad de `agregar_comentario`.
        """
        if actor.puede_reabrir(requerimiento):
            requerimiento.reabrir(actor)
