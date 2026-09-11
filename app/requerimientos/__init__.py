"""Módulo de dominio: Incidentes y Solicitudes (Requerimientos de la Mesa de Ayuda).

`ServicioRequerimientos` (capa de Aplicación) deliberadamente NO se reexporta
aquí: depende de `app.notificaciones`, que a su vez importa
`app.requerimientos.eventos` — reexportarlo forzaría un import circular al
inicializar este paquete. Impórtalo directo:
`from app.requerimientos.servicios import ServicioRequerimientos`.
"""

from app.requerimientos.dominio import (
    CategoriaSolicitud,
    EstadoRequerimiento,
    Incidente,
    Requerimiento,
    Severidad,
    Solicitud,
    TipoRequerimiento,
)
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    RequerimientoError,
    RequerimientoNoEncontradoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)
from app.requerimientos.fabrica import FabricaRequerimientos
from app.requerimientos.repositorio import RepositorioRequerimientos

__all__ = [
    "Requerimiento",
    "Incidente",
    "Solicitud",
    "EstadoRequerimiento",
    "TipoRequerimiento",
    "Severidad",
    "CategoriaSolicitud",
    "EventoRequerimiento",
    "TipoEventoRequerimiento",
    "FabricaRequerimientos",
    "RepositorioRequerimientos",
    "RequerimientoError",
    "TransicionInvalidaError",
    "TecnicoNoAsignadoError",
    "NotaResolucionRequeridaError",
    "PermisoDenegadoError",
    "RequerimientoNoEncontradoError",
]
