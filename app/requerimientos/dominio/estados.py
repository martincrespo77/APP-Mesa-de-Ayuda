"""Enumeraciones de estado y tipo del dominio de requerimientos.

`EstadoRequerimiento` no incluye un valor `CREADO`: el requerimiento nace
directamente en `ABIERTO` (el "[ CREADO ]" del diagrama de la especificación
de negocio es el instante de creación, auditado como
`TipoEventoRequerimiento.CREACION`, no un estado persistente).
"""

from enum import StrEnum


class EstadoRequerimiento(StrEnum):
    """Ciclo de vida de un `Requerimiento`."""

    ABIERTO = "ABIERTO"
    EN_ANALISIS = "EN_ANALISIS"
    EN_PROGRESO = "EN_PROGRESO"
    RESUELTO = "RESUELTO"
    CERRADO = "CERRADO"
    CANCELADO = "CANCELADO"


class TipoRequerimiento(StrEnum):
    """Discriminador polimórfico entre las dos jerarquías de `Requerimiento`."""

    INCIDENTE = "INCIDENTE"
    SOLICITUD = "SOLICITUD"
