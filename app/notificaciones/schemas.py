"""Esquemas Pydantic v2 (DTOs) del módulo de notificaciones."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.requerimientos.eventos import TipoEventoRequerimiento


class NotificacionResponse(BaseModel):
    """Representación pública de una `Notificacion`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supervisor_id: uuid.UUID
    empleado_supervisado_id: uuid.UUID
    requerimiento_id: uuid.UUID
    tipo_evento: TipoEventoRequerimiento
    detalle: str
    timestamp: datetime
    leida: bool
