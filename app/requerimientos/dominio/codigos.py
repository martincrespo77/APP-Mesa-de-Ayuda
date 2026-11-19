"""Códigos estables del dominio de requerimientos (estado y tipo).

Son identificadores inmutables para persistencia, DTOs y discriminadores
polimórficos — igual que `RolUsuario` para la jerarquía `Usuario` —, nunca
para decidir comportamiento con `if`. El comportamiento de cada estado vive
en su clase del paquete `estados/` (Patrón State); `FabricaEstados` es el
único lugar que traduce un `EstadoRequerimiento` a su clase.

`EstadoRequerimiento` no incluye un valor `CREADO`: el requerimiento nace
directamente en `ABIERTO` (el "[ CREADO ]" del diagrama de la especificación
de negocio es el instante de creación, auditado como
`TipoEventoRequerimiento.CREACION`, no un estado persistente).
"""

from enum import StrEnum


class EstadoRequerimiento(StrEnum):
    """Código persistible de cada estado del ciclo de vida de un `Requerimiento`."""

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
