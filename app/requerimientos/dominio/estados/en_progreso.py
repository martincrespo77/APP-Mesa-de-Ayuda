"""Estado `EN_PROGRESO`: el técnico asignado está trabajando el ticket."""

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.en_atencion import EstadoEnAtencion
from app.requerimientos.dominio.estados.resuelto import EstadoResuelto


class EstadoEnProgreso(EstadoEnAtencion):
    """EN_PROGRESO -> RESUELTO | CANCELADO; admite derivación."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.EN_PROGRESO

    def resolver(self) -> EstadoTicket:
        return EstadoResuelto()
