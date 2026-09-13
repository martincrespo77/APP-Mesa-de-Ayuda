"""Evento de dominio: registro inmutable de auditoría de un requerimiento.

`EventoRequerimiento` es generado por la propia entidad `Requerimiento`
(Information Expert: ella conoce los valores previos/nuevos de cada
transición) y luego es consumido por el módulo `notificaciones/` mediante
el patrón Observer, sin que `requerimientos` dependa de `notificaciones`.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class TipoEventoRequerimiento(StrEnum):
    """Naturaleza del cambio auditado sobre un requerimiento."""

    CREACION = "CREACION"
    CAMBIO_ESTADO = "CAMBIO_ESTADO"
    ASIGNACION = "ASIGNACION"
    RESOLUCION = "RESOLUCION"
    CIERRE = "CIERRE"
    CANCELACION = "CANCELACION"
    COMENTARIO = "COMENTARIO"
    DERIVACION = "DERIVACION"
    REAPERTURA = "REAPERTURA"


@dataclass(frozen=True)
class EventoRequerimiento:
    """Hecho inmutable ocurrido sobre un requerimiento, con fines de auditoría."""

    requerimiento_id: uuid.UUID
    tipo_evento: TipoEventoRequerimiento
    autor_id: uuid.UUID
    detalle: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
