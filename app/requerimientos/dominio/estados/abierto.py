"""Estado `ABIERTO`: el ticket recién creado, que nadie tomó todavía."""

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.cancelable import EstadoCancelable
from app.requerimientos.dominio.estados.en_analisis import EstadoEnAnalisis


class EstadoAbierto(EstadoCancelable):
    """ABIERTO -> EN_ANALISIS | CANCELADO."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.ABIERTO

    def iniciar_analisis(self) -> EstadoTicket:
        return EstadoEnAnalisis()

    def esta_abierto(self) -> bool:
        return True
