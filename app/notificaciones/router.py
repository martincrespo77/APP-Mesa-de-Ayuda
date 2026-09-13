"""Endpoints FastAPI del módulo de notificaciones.

Gateados con `requerir_rol(SUPERVISOR)`: son las únicas destinatarias de
`Notificacion` (ver `app/infraestructura/observador_notificaciones.py`).
"""

import uuid

from fastapi import APIRouter, Depends

from app.compartido.dominio import RolUsuario
from app.deps import obtener_servicio_notificaciones, obtener_usuario_actual, requerir_rol
from app.notificaciones.schemas import NotificacionResponse
from app.notificaciones.servicios import ServicioNotificaciones
from app.usuarios.dominio import Usuario

router = APIRouter(
    prefix="/notificaciones",
    tags=["notificaciones"],
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)


@router.get("", response_model=list[NotificacionResponse])
def listar_mis_notificaciones(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioNotificaciones = Depends(obtener_servicio_notificaciones),
) -> list[NotificacionResponse]:
    return [
        NotificacionResponse.model_validate(n) for n in servicio.listar_mias(usuario_actual.id)
    ]


@router.patch("/{notificacion_id}/leida", response_model=NotificacionResponse)
def marcar_notificacion_leida(
    notificacion_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioNotificaciones = Depends(obtener_servicio_notificaciones),
) -> NotificacionResponse:
    notificacion = servicio.marcar_leida(notificacion_id, usuario_actual.id)
    return NotificacionResponse.model_validate(notificacion)
