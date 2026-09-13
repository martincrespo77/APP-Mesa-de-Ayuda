"""Endpoints FastAPI del módulo de supervisión.

Todos los endpoints están gateados con `requerir_rol(SUPERVISOR)`: no hay
contraparte de dominio para "quién puede administrar supervisiones" (es
pura administración de cuentas, igual que el resto de `usuarios/router.py`),
así que se centraliza acá en vez de duplicarlo en la entidad.
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.compartido.dominio import RolUsuario
from app.deps import obtener_servicio_supervision, obtener_usuario_actual, requerir_rol
from app.supervision.schemas import AsignarSupervisionRequest, RelacionSupervisionResponse
from app.supervision.servicios import ServicioSupervision
from app.usuarios.dominio import Usuario

router = APIRouter(
    prefix="/supervisiones",
    tags=["supervision"],
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)


@router.post("", response_model=RelacionSupervisionResponse, status_code=status.HTTP_201_CREATED)
def asignar_supervision(
    datos: AsignarSupervisionRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioSupervision = Depends(obtener_servicio_supervision),
) -> RelacionSupervisionResponse:
    """Asigna al Supervisor autenticado como supervisor del `supervisado_id` dado."""
    relacion = servicio.asignar(usuario_actual.id, datos.supervisado_id)
    return RelacionSupervisionResponse.model_validate(relacion)


@router.delete("/{supervisado_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_supervision(
    supervisado_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioSupervision = Depends(obtener_servicio_supervision),
) -> None:
    servicio.remover(usuario_actual.id, supervisado_id)


@router.get("", response_model=list[RelacionSupervisionResponse])
def listar_mis_supervisados(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioSupervision = Depends(obtener_servicio_supervision),
) -> list[RelacionSupervisionResponse]:
    """Lista las relaciones donde el Supervisor autenticado es el supervisor."""
    return [
        RelacionSupervisionResponse.model_validate(r)
        for r in servicio.listar_supervisados_de(usuario_actual.id)
    ]
