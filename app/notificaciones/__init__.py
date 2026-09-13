"""Módulo de dominio: notificaciones vía patrón Observer.

Consume `EventoRequerimiento` (generado en `app/requerimientos/`) sin que
ese módulo conozca la existencia de `notificaciones`, evitando el
acoplamiento inverso descrito en 03_ARQUITECTURA_Y_PATRONES.md.
"""

from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.dominio import Notificacion
from app.notificaciones.excepciones import NotificacionError, NotificacionNoEncontradaError
from app.notificaciones.observador import ObservadorRequerimiento
from app.notificaciones.observador_logger import ObservadorLogger
from app.notificaciones.repositorio import RepositorioNotificaciones
from app.notificaciones.servicios import ServicioNotificaciones

__all__ = [
    "ObservadorRequerimiento",
    "DespachadorEventos",
    "ObservadorLogger",
    "Notificacion",
    "NotificacionError",
    "NotificacionNoEncontradaError",
    "RepositorioNotificaciones",
    "ServicioNotificaciones",
]
