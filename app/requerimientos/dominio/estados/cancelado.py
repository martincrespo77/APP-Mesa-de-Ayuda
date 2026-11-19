"""Estado `CANCELADO`: el ticket fue desestimado antes de resolverse."""

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.terminal import EstadoTerminal


class EstadoCancelado(EstadoTerminal):
    """Estado final tras una cancelación: ninguna transición es válida."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.CANCELADO
