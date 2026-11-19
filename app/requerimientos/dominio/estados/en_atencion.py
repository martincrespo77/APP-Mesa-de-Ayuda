"""Clase abstracta `EstadoEnAtencion`: el ticket ya está en manos de la mesa.

EN_ANALISIS y EN_PROGRESO son los únicos estados desde los que el técnico
asignado puede derivar el ticket a otro técnico (interconsulta).
"""

from abc import ABC

from app.requerimientos.dominio.estados.cancelable import EstadoCancelable


class EstadoEnAtencion(EstadoCancelable, ABC):
    """Estado de trabajo activo sobre el ticket: admite derivación."""

    def exigir_admite_derivacion(self) -> None:
        """La derivación es válida mientras el ticket está siendo atendido."""
