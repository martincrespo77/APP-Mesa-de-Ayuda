"""Esquemas Pydantic v2 (DTOs) del módulo de supervisión."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AsignarSupervisionRequest(BaseModel):
    """Id del Operador/Técnico a supervisar."""

    supervisado_id: uuid.UUID


class RelacionSupervisionResponse(BaseModel):
    """Representación pública de una `RelacionSupervision`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    supervisor_id: uuid.UUID
    supervisado_id: uuid.UUID
    fecha_asignacion: datetime
