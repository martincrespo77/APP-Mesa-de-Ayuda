"""Clase abstracta `EstadoTerminal`: fin del ciclo de vida (CERRADO / CANCELADO).

Un ticket terminal no admite ninguna transición (herencia del rechazo por
defecto de `EstadoTicket`) ni comentarios de seguimiento.
"""

from abc import ABC

from app.requerimientos.dominio.estados.base import EstadoTicket


class EstadoTerminal(EstadoTicket, ABC):
    """Estado final: el ticket queda congelado."""

    def exigir_admite_comentarios(self) -> None:
        raise self._transicion_invalida("agregar comentarios a")
