"""Servicio de aplicación: casos de uso del módulo de notificaciones."""

import uuid
from typing import TYPE_CHECKING

from app.notificaciones.dominio import Notificacion
from app.notificaciones.excepciones import NotificacionNoEncontradaError
from app.notificaciones.repositorio import RepositorioNotificaciones

if TYPE_CHECKING:
    # Solo para tipos: usuarios.dominio -> supervision -> notificaciones es un ciclo.
    from app.usuarios.dominio import Usuario


class ServicioNotificaciones:
    """Orquesta la consulta y el marcado de lectura de `Notificacion`."""

    def __init__(self, repositorio: RepositorioNotificaciones) -> None:
        self._repositorio = repositorio

    def listar_mias(self, supervisor_id: uuid.UUID) -> list[Notificacion]:
        return self._repositorio.listar_por_supervisor(supervisor_id)

    def marcar_leida(self, notificacion_id: uuid.UUID, actor: "Usuario") -> Notificacion:
        """Le pide a la notificación que se marque leída por ese supervisor
        (ella valida que le pertenezca)."""
        notificacion = self._repositorio.buscar_por_id(notificacion_id)
        if notificacion is None:
            raise NotificacionNoEncontradaError(
                f"No existe una notificación con id '{notificacion_id}' para este supervisor."
            )
        notificacion.marcar_leida_por(actor)
        self._repositorio.guardar(notificacion)
        return notificacion
