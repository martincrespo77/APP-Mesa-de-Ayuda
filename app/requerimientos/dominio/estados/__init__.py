"""Patrón State del ciclo de vida de `Requerimiento`.

    EstadoTicket (abstracta: todo rechazado por defecto)
    ├── EstadoCancelable (abstracta: -> CANCELADO)
    │   ├── EstadoAbierto
    │   └── EstadoEnAtencion (abstracta: admite derivación)
    │       ├── EstadoEnAnalisis
    │       └── EstadoEnProgreso
    ├── EstadoResuelto
    └── EstadoTerminal (abstracta: sin comentarios)
        ├── EstadoCerrado
        └── EstadoCancelado

Reexporta también los códigos `EstadoRequerimiento` / `TipoRequerimiento`
(compatibilidad con `from app.requerimientos.dominio.estados import ...`).
"""

from app.requerimientos.dominio.codigos import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.estados.abierto import EstadoAbierto
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.cancelado import EstadoCancelado
from app.requerimientos.dominio.estados.cerrado import EstadoCerrado
from app.requerimientos.dominio.estados.en_analisis import EstadoEnAnalisis
from app.requerimientos.dominio.estados.en_progreso import EstadoEnProgreso
from app.requerimientos.dominio.estados.fabrica import FabricaEstados
from app.requerimientos.dominio.estados.resuelto import EstadoResuelto

__all__ = [
    "EstadoAbierto",
    "EstadoCancelado",
    "EstadoCerrado",
    "EstadoEnAnalisis",
    "EstadoEnProgreso",
    "EstadoRequerimiento",
    "EstadoResuelto",
    "EstadoTicket",
    "FabricaEstados",
    "TipoRequerimiento",
]
