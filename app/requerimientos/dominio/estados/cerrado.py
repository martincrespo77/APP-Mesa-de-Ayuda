"""Estado `CERRADO`: el ticket terminó con cierre de conformidad."""

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.terminal import EstadoTerminal


class EstadoCerrado(EstadoTerminal):
    """Estado final tras la conformidad: ninguna transición es válida."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.CERRADO
