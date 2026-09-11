"""Módulo de dominio: Incidentes y Solicitudes (Requerimientos de la Mesa de Ayuda)."""

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
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)
from app.requerimientos.fabrica import FabricaRequerimientos

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
    "RequerimientoError",
    "TransicionInvalidaError",
    "TecnicoNoAsignadoError",
    "NotaResolucionRequeridaError",
    "PermisoDenegadoError",
]
