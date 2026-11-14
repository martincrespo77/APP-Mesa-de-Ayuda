"""Clase abstracta `EstadoCancelable`: estados previos a la resolución.

ABIERTO, EN_ANALISIS y EN_PROGRESO comparten una única transición: pueden
pasar a CANCELADO. Quién puede cancelar en cada uno lo decide el actor.
"""

from abc import ABC

from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.cancelado import EstadoCancelado


class EstadoCancelable(EstadoTicket, ABC):
    """Estado todavía no resuelto: admite la cancelación del ticket."""

    def cancelar(self) -> EstadoTicket:
        return EstadoCancelado()
