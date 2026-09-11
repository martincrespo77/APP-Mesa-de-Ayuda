"""Observador concreto: auditoría por logging estándar.

Es el único observador que vive en el dominio, porque solo depende de la
librería estándar (`logging`). Observadores que requieran infraestructura
externa (SMTP, colas, push) se implementan en `app/infraestructura/` y se
suscriben del mismo modo, sin modificar `DespachadorEventos`.
"""

import logging

from app.notificaciones.observador import ObservadorRequerimiento
from app.requerimientos.eventos import EventoRequerimiento

_logger = logging.getLogger("mesa_de_ayuda.auditoria")


class ObservadorLogger(ObservadorRequerimiento):
    """Registra cada evento de requerimiento en el log de auditoría."""

    def actualizar(self, evento: EventoRequerimiento) -> None:
        _logger.info(
            "Evento %s sobre requerimiento %s por autor %s: %s",
            evento.tipo_evento.value,
            evento.requerimiento_id,
            evento.autor_id,
            evento.detalle,
        )
