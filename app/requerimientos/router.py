"""Endpoints FastAPI del módulo de requerimientos.

Ninguna transición usa `requerir_rol(...)`: la propia entidad `Requerimiento`
ya valida el rol/identidad del actor (Information Expert, Paso 2) y lanza
`PermisoDenegadoError`, traducida a HTTP 403 por el exception handler de
`app/main.py`. Duplicar el chequeo aquí repetiría la misma regla de
negocio en dos capas.
"""

import uuid

from fastapi import APIRouter, Depends

from app.deps import obtener_servicio_requerimientos, obtener_usuario_actual
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import TipoRequerimiento
from app.requerimientos.dominio.incidente import Incidente
from app.requerimientos.excepciones import RequerimientoNoEncontradoError
from app.requerimientos.schemas import (
    AsignarTecnicoRequest,
    CrearIncidenteRequest,
    CrearRequerimientoRequest,
    IncidenteResponse,
    RequerimientoResponse,
    ResolverRequest,
    SolicitudResponse,
)
from app.requerimientos.servicios import ServicioRequerimientos
from app.usuarios.dominio import Usuario

router = APIRouter(prefix="/requerimientos", tags=["requerimientos"])


def _a_respuesta(requerimiento: Requerimiento) -> IncidenteResponse | SolicitudResponse:
    """Convierte la entidad de dominio en el schema de respuesta polimórfico correcto."""
    if isinstance(requerimiento, Incidente):
        return IncidenteResponse.model_validate(requerimiento)
    return SolicitudResponse.model_validate(requerimiento)


@router.post("", response_model=RequerimientoResponse, status_code=201)
def crear_requerimiento(
    datos: CrearRequerimientoRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    """Crea un Incidente o una Solicitud (según `tipo`) a nombre del usuario actual."""
    if isinstance(datos, CrearIncidenteRequest):
        requerimiento = servicio.crear(
            TipoRequerimiento.INCIDENTE,
            titulo=datos.titulo,
            descripcion=datos.descripcion,
            solicitante_id=usuario_actual.id,
            severidad=datos.severidad,
            pasos_reproduccion=datos.pasos_reproduccion,
            servicio_afectado=datos.servicio_afectado,
        )
    else:
        requerimiento = servicio.crear(
            TipoRequerimiento.SOLICITUD,
            titulo=datos.titulo,
            descripcion=datos.descripcion,
            solicitante_id=usuario_actual.id,
            categoria=datos.categoria,
            fecha_limite=datos.fecha_limite,
            impacto_estimado=datos.impacto_estimado,
        )
    return _a_respuesta(requerimiento)


@router.get("", response_model=list[RequerimientoResponse])
def listar_requerimientos(
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> list[IncidenteResponse | SolicitudResponse]:
    """Aplica la visibilidad de la matriz de roles (Solicitante ve solo lo propio)."""
    visibles = servicio.listar_visibles_para(usuario_actual.rol, usuario_actual.id)
    return [_a_respuesta(req) for req in visibles]


@router.get("/{requerimiento_id}", response_model=RequerimientoResponse)
def obtener_requerimiento(
    requerimiento_id: uuid.UUID,
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.obtener_por_id(requerimiento_id)
    if requerimiento is None:
        raise RequerimientoNoEncontradoError(
            f"No existe un requerimiento con id '{requerimiento_id}'."
        )
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/iniciar-analisis", response_model=RequerimientoResponse)
def iniciar_analisis(
    requerimiento_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.iniciar_analisis(
        requerimiento_id, usuario_actual.id, usuario_actual.rol
    )
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/asignar-tecnico", response_model=RequerimientoResponse)
def asignar_tecnico(
    requerimiento_id: uuid.UUID,
    datos: AsignarTecnicoRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.asignar_tecnico(
        requerimiento_id, datos.tecnico_id, usuario_actual.id, usuario_actual.rol
    )
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/iniciar-progreso", response_model=RequerimientoResponse)
def iniciar_progreso(
    requerimiento_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.iniciar_progreso(
        requerimiento_id, usuario_actual.id, usuario_actual.rol
    )
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/resolver", response_model=RequerimientoResponse)
def resolver(
    requerimiento_id: uuid.UUID,
    datos: ResolverRequest,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.resolver(
        requerimiento_id, datos.nota_resolucion, usuario_actual.id, usuario_actual.rol
    )
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/cerrar", response_model=RequerimientoResponse)
def cerrar(
    requerimiento_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.cerrar(requerimiento_id, usuario_actual.id, usuario_actual.rol)
    return _a_respuesta(requerimiento)


@router.post("/{requerimiento_id}/cancelar", response_model=RequerimientoResponse)
def cancelar(
    requerimiento_id: uuid.UUID,
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
    servicio: ServicioRequerimientos = Depends(obtener_servicio_requerimientos),
) -> IncidenteResponse | SolicitudResponse:
    requerimiento = servicio.cancelar(requerimiento_id, usuario_actual.id, usuario_actual.rol)
    return _a_respuesta(requerimiento)
