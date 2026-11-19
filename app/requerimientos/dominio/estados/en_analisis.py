"""Estado `EN_ANALISIS`: la mesa de ayuda hace el triage y asigna un técnico."""

from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.en_atencion import EstadoEnAtencion
from app.requerimientos.dominio.estados.en_progreso import EstadoEnProgreso


class EstadoEnAnalisis(EstadoEnAtencion):
    """EN_ANALISIS -> EN_PROGRESO | CANCELADO; admite asignación y derivación."""

    @property
    def codigo(self) -> EstadoRequerimiento:
        return EstadoRequerimiento.EN_ANALISIS

    def exigir_admite_asignacion(self) -> None:
        """Solo durante el análisis se asigna el técnico responsable."""

    def iniciar_progreso(self) -> EstadoTicket:
        return EstadoEnProgreso()
