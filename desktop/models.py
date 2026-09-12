"""Modelos de datos propios del cliente de escritorio (Paso 6).

`desktop/` es completamente independiente del backend (doc05: no importa
clases ni modelos de `app/`). Estos tipos coinciden por *contrato* con lo
que devuelve la API (mismos valores de enum, mismos nombres de campo
JSON) pero son una implementación separada, propia de esta capa.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class RolUsuario(StrEnum):
    SOLICITANTE = "SOLICITANTE"
    OPERADOR = "OPERADOR"
    TECNICO = "TECNICO"
    SUPERVISOR = "SUPERVISOR"


class EstadoRequerimiento(StrEnum):
    ABIERTO = "ABIERTO"
    EN_ANALISIS = "EN_ANALISIS"
    EN_PROGRESO = "EN_PROGRESO"
    RESUELTO = "RESUELTO"
    CERRADO = "CERRADO"
    CANCELADO = "CANCELADO"


class TipoRequerimiento(StrEnum):
    INCIDENTE = "INCIDENTE"
    SOLICITUD = "SOLICITUD"


class Severidad(StrEnum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class CategoriaSolicitud(StrEnum):
    NUEVO_SERVICIO = "NUEVO_SERVICIO"
    CAMBIO_ABONO = "CAMBIO_ABONO"
    CONSULTA_ADMINISTRATIVA = "CONSULTA_ADMINISTRATIVA"
    FACTURACION = "FACTURACION"


class TipoEventoRequerimiento(StrEnum):
    CREACION = "CREACION"
    CAMBIO_ESTADO = "CAMBIO_ESTADO"
    ASIGNACION = "ASIGNACION"
    RESOLUCION = "RESOLUCION"
    CIERRE = "CIERRE"
    CANCELACION = "CANCELACION"


@dataclass(frozen=True)
class UsuarioDTO:
    """Datos de sesión del usuario autenticado (claims del JWT + perfil)."""

    id: uuid.UUID
    nombre_completo: str
    email: str
    rol: RolUsuario
    activo: bool

    @staticmethod
    def desde_json(datos: dict[str, Any]) -> "UsuarioDTO":
        return UsuarioDTO(
            id=uuid.UUID(datos["id"]),
            nombre_completo=datos["nombre_completo"],
            email=datos["email"],
            rol=RolUsuario(datos["rol"]),
            activo=datos["activo"],
        )


@dataclass(frozen=True)
class EventoDTO:
    """Un evento del historial de auditoría de un requerimiento."""

    id: uuid.UUID
    tipo_evento: TipoEventoRequerimiento
    autor_id: uuid.UUID
    detalle: str
    timestamp: datetime

    @staticmethod
    def desde_json(datos: dict[str, Any]) -> "EventoDTO":
        return EventoDTO(
            id=uuid.UUID(datos["id"]),
            tipo_evento=TipoEventoRequerimiento(datos["tipo_evento"]),
            autor_id=uuid.UUID(datos["autor_id"]),
            detalle=datos["detalle"],
            timestamp=datetime.fromisoformat(datos["timestamp"]),
        )


@dataclass(frozen=True)
class RequerimientoDTO:
    """Representación uniforme de un Incidente o una Solicitud.

    Los campos específicos de cada tipo quedan en `None` cuando no
    aplican (p. ej. `severidad` en una Solicitud): es más simple para una
    tabla/formulario de Qt que mantener una jerarquía de clases paralela
    solo para mostrar datos — la jerarquía real vive en el dominio del
    backend, no acá.
    """

    id: uuid.UUID
    tipo: TipoRequerimiento
    titulo: str
    descripcion: str
    solicitante_id: uuid.UUID
    estado: EstadoRequerimiento
    fecha_creacion: datetime
    tecnico_asignado_id: uuid.UUID | None
    nota_resolucion: str | None
    historial: tuple[EventoDTO, ...]
    # Específicos de Incidente
    severidad: Severidad | None = None
    pasos_reproduccion: str | None = None
    servicio_afectado: str | None = None
    # Específicos de Solicitud
    categoria: CategoriaSolicitud | None = None
    fecha_limite: datetime | None = None
    impacto_estimado: str | None = None

    @staticmethod
    def desde_json(datos: dict[str, Any]) -> "RequerimientoDTO":
        tipo = TipoRequerimiento(datos["tipo"])
        tecnico_asignado_id = datos["tecnico_asignado_id"]
        comunes: dict[str, Any] = {
            "id": uuid.UUID(datos["id"]),
            "tipo": tipo,
            "titulo": datos["titulo"],
            "descripcion": datos["descripcion"],
            "solicitante_id": uuid.UUID(datos["solicitante_id"]),
            "estado": EstadoRequerimiento(datos["estado"]),
            "fecha_creacion": datetime.fromisoformat(datos["fecha_creacion"]),
            "tecnico_asignado_id": (
                uuid.UUID(tecnico_asignado_id) if tecnico_asignado_id is not None else None
            ),
            "nota_resolucion": datos["nota_resolucion"],
            "historial": tuple(EventoDTO.desde_json(e) for e in datos["historial"]),
        }
        if tipo is TipoRequerimiento.INCIDENTE:
            return RequerimientoDTO(
                **comunes,
                severidad=Severidad(datos["severidad"]),
                pasos_reproduccion=datos["pasos_reproduccion"],
                servicio_afectado=datos["servicio_afectado"],
            )
        return RequerimientoDTO(
            **comunes,
            categoria=CategoriaSolicitud(datos["categoria"]),
            fecha_limite=datetime.fromisoformat(datos["fecha_limite"]),
            impacto_estimado=datos["impacto_estimado"],
        )
