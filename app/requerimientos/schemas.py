"""Esquemas Pydantic v2 del módulo de requerimientos: DTOs de request/response.

Serialización polimórfica de `Incidente`/`Solicitud` vía Discriminated
Union nativo de Pydantic v2 (campo `tipo`), tanto para las respuestas como
para el body de creación — decisión de grilling del 2026-09-11, en lugar
de una `SchemaFactory` manual (esa técnica, de
`13_serializacion_polimorfica.md`, es para los DbSchemas de Mongo del
Paso 5, no para esta capa de presentación).

Cada request de creación sabe traducirse a su Value Object de dominio
(`a_datos()`): el router no necesita `isinstance` para saber qué tipo llegó.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.compartido.dominio import ServicioComunicarlos
from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.creacion import DatosIncidente, DatosRequerimiento, DatosSolicitud
from app.requerimientos.dominio.incidente import CategoriaIncidente, UrgenciaIncidente
from app.requerimientos.dominio.solicitud import CategoriaSolicitud
from app.requerimientos.eventos import TipoEventoRequerimiento

# -- Requests de creación -----------------------------------------------------


class CrearIncidenteRequest(BaseModel):
    tipo: Literal["INCIDENTE"] = "INCIDENTE"
    titulo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    urgencia: UrgenciaIncidente
    categoria: CategoriaIncidente
    servicio: ServicioComunicarlos
    pasos_reproduccion: str = Field(min_length=1)

    def a_datos(self) -> DatosRequerimiento:
        return DatosIncidente(
            titulo=self.titulo,
            descripcion=self.descripcion,
            servicio=self.servicio,
            urgencia=self.urgencia,
            categoria=self.categoria,
            pasos_reproduccion=self.pasos_reproduccion,
        )


class CrearSolicitudRequest(BaseModel):
    tipo: Literal["SOLICITUD"] = "SOLICITUD"
    titulo: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    categoria: CategoriaSolicitud
    servicio: ServicioComunicarlos

    def a_datos(self) -> DatosRequerimiento:
        return DatosSolicitud(
            titulo=self.titulo,
            descripcion=self.descripcion,
            servicio=self.servicio,
            categoria=self.categoria,
        )


CrearRequerimientoRequest = Annotated[
    CrearIncidenteRequest | CrearSolicitudRequest, Field(discriminator="tipo")
]


# -- Requests de transición ---------------------------------------------------


class AsignarTecnicoRequest(BaseModel):
    tecnico_id: uuid.UUID


class ResolverRequest(BaseModel):
    nota_resolucion: str = Field(min_length=1)


class AgregarComentarioRequest(BaseModel):
    texto: str = Field(min_length=1)


class DerivarInterconsultaRequest(BaseModel):
    tecnico_destino_id: uuid.UUID


# -- Responses -----------------------------------------------------------------


class EventoResponse(BaseModel):
    """Un evento de auditoría del historial de un requerimiento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo_evento: TipoEventoRequerimiento
    autor_id: uuid.UUID
    detalle: str
    timestamp: datetime


class ComentarioResponse(BaseModel):
    """Un comentario de seguimiento sobre un requerimiento."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    requerimiento_id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
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
    comentarios: list[ComentarioResponse]


class IncidenteResponse(_RequerimientoResponseBase):
    tipo: Literal["INCIDENTE"] = "INCIDENTE"
    urgencia: UrgenciaIncidente
    categoria: CategoriaIncidente
    servicio: ServicioComunicarlos
    pasos_reproduccion: str


class SolicitudResponse(_RequerimientoResponseBase):
    tipo: Literal["SOLICITUD"] = "SOLICITUD"
    categoria: CategoriaSolicitud
    servicio: ServicioComunicarlos


RequerimientoResponse = Annotated[
    IncidenteResponse | SolicitudResponse, Field(discriminator="tipo")
]
