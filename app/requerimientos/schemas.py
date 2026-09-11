"""Esquemas Pydantic v2 del módulo de requerimientos: DTOs de request/response.

Serialización polimórfica de `Incidente`/`Solicitud` vía Discriminated
Union nativo de Pydantic v2 (campo `tipo`), tanto para las respuestas como
para el body de creación — decisión de grilling del 2026-09-11, en lugar
de una `SchemaFactory` manual (esa técnica, de
`13_serializacion_polimorfica.md`, es para los DbSchemas de Mongo del
Paso 5, no para esta capa de presentación).
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.requerimientos.dominio.estados import EstadoRequerimiento
from app.requerimientos.dominio.incidente import Severidad
from app.requerimientos.dominio.solicitud import CategoriaSolicitud
from app.requerimientos.eventos import TipoEventoRequerimiento

# -- Requests de creación -----------------------------------------------------


class CrearIncidenteRequest(BaseModel):
    tipo: Literal["INCIDENTE"] = "INCIDENTE"
    titulo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    severidad: Severidad
    pasos_reproduccion: str = Field(min_length=1)
    servicio_afectado: str = Field(min_length=1)


class CrearSolicitudRequest(BaseModel):
    tipo: Literal["SOLICITUD"] = "SOLICITUD"
    titulo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    categoria: CategoriaSolicitud
    fecha_limite: datetime
    impacto_estimado: str = Field(min_length=1)


CrearRequerimientoRequest = Annotated[
    CrearIncidenteRequest | CrearSolicitudRequest, Field(discriminator="tipo")
]


# -- Requests de transición ---------------------------------------------------


class AsignarTecnicoRequest(BaseModel):
    tecnico_id: uuid.UUID


class ResolverRequest(BaseModel):
    nota_resolucion: str = Field(min_length=1)


# -- Responses -----------------------------------------------------------------


class EventoResponse(BaseModel):
    """Un evento de auditoría del historial de un requerimiento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_evento: TipoEventoRequerimiento
    autor_id: uuid.UUID
    detalle: str
    timestamp: datetime


class _RequerimientoResponseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    titulo: str
    descripcion: str
    solicitante_id: uuid.UUID
    estado: EstadoRequerimiento
    fecha_creacion: datetime
    tecnico_asignado_id: uuid.UUID | None
    nota_resolucion: str | None
    historial: list[EventoResponse]


class IncidenteResponse(_RequerimientoResponseBase):
    tipo: Literal["INCIDENTE"] = "INCIDENTE"
    severidad: Severidad
    pasos_reproduccion: str
    servicio_afectado: str


class SolicitudResponse(_RequerimientoResponseBase):
    tipo: Literal["SOLICITUD"] = "SOLICITUD"
    categoria: CategoriaSolicitud
    fecha_limite: datetime
    impacto_estimado: str


RequerimientoResponse = Annotated[
    IncidenteResponse | SolicitudResponse, Field(discriminator="tipo")
]
