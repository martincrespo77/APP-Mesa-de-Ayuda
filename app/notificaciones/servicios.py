"""Servicio de aplicación: casos de uso del módulo de notificaciones."""

import uuid

from app.notificaciones.dominio import Notificacion
from app.notificaciones.excepciones import NotificacionNoEncontradaError
from app.notificaciones.repositorio import RepositorioNotificaciones


class ServicioNotificaciones:
    """Orquesta la consulta y el marcado de lectura de `Notificacion`."""

    def __init__(self, repositorio: RepositorioNotificaciones) -> None:
        self._repositorio = repositorio

    def listar_mias(self, supervisor_id: uuid.UUID) -> list[Notificacion]:
        return self._repositorio.listar_por_supervisor(supervisor_id)

    def marcar_leida(self, notificacion_id: uuid.UUID, supervisor_id: uuid.UUID) -> Notificacion:
        """Marca leída una notificación, exigiendo que pertenezca a ese supervisor."""
        notificacion = self._repositorio.buscar_por_id(notificacion_id)
        if notificacion is None or notificacion.supervisor_id != supervisor_id:
            raise NotificacionNoEncontradaError(
                f"No existe una notificación con id '{notificacion_id}' para este supervisor."
            )
        notificacion.marcar_leida()
        self._repositorio.guardar(notificacion)
        return notificacion
