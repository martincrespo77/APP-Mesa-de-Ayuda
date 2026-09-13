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


class UrgenciaIncidente(StrEnum):
    CRITICO = "CRITICO"
    IMPORTANTE = "IMPORTANTE"
    MENOR = "MENOR"


class CategoriaIncidente(StrEnum):
    SERVICIO_INACCESIBLE = "SERVICIO_INACCESIBLE"
    BLOQUEO_SIM = "BLOQUEO_SIM"
    PERDIDA_O_DESTRUCCION_DE_EQUIPO = "PERDIDA_O_DESTRUCCION_DE_EQUIPO"


class ServicioComunicarlos(StrEnum):
    TELEFONIA_CELULAR = "TELEFONIA_CELULAR"
    INTERNET_BANDA_ANCHA = "INTERNET_BANDA_ANCHA"
    TELEVISION = "TELEVISION"


class CategoriaSolicitud(StrEnum):
    ALTA_SERVICIO = "ALTA_SERVICIO"
    BAJA_SERVICIO = "BAJA_SERVICIO"


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
    # Específico de Incidente
    urgencia: UrgenciaIncidente | None = None
    pasos_reproduccion: str | None = None
    # Compartidos entre Incidente y Solicitud
    categoria: CategoriaIncidente | CategoriaSolicitud | None = None
    servicio: ServicioComunicarlos | None = None

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
                urgencia=UrgenciaIncidente(datos["urgencia"]),
                categoria=CategoriaIncidente(datos["categoria"]),
                servicio=ServicioComunicarlos(datos["servicio"]),
                pasos_reproduccion=datos["pasos_reproduccion"],
            )
        return RequerimientoDTO(
            **comunes,
            categoria=CategoriaSolicitud(datos["categoria"]),
            servicio=ServicioComunicarlos(datos["servicio"]),
        )
