"""Endpoints FastAPI del módulo de usuarios: login y administración.

Todos los endpoints salvo `/login` y `/me` están gateados con
`requerir_rol(SUPERVISOR)`, siguiendo la matriz de roles de
`02_OBJETIVO_Y_DOMINIO_NEGOCIO.md` ("Administrar usuarios": solo
Supervisor). No hay auto-registro: las cuentas las crea un Supervisor.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import crear_token_acceso, obtener_password_hash, verificar_password
from app.compartido.dominio import RolUsuario
from app.deps import obtener_servicio_usuarios, obtener_usuario_actual, requerir_rol
from app.usuarios.dominio import Usuario
from app.usuarios.schemas import (
    CambiarRolRequest,
    TokenResponse,
    UsuarioCreateRequest,
    UsuarioResponse,
)
from app.usuarios.servicios import ServicioUsuarios

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.post("/login", response_model=TokenResponse)
def login(
    credenciales: OAuth2PasswordRequestForm = Depends(),
    servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios),
) -> TokenResponse:
    """Autentica por email (campo `username` del form OAuth2) + password."""
    usuario = servicio.obtener_por_email(credenciales.username)
    credenciales_validas = usuario is not None and verificar_password(
        credenciales.password, usuario.password_hash
    )
    if not credenciales_validas or usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = crear_token_acceso(usuario.id, usuario.rol)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UsuarioResponse)
def obtener_mi_perfil(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> UsuarioResponse:
    """Cualquier usuario autenticado puede consultar su propio perfil."""
    return UsuarioResponse.model_validate(usuario_actual)


@router.post(
    "",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)
def crear_usuario(
    datos: UsuarioCreateRequest, servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios)
) -> UsuarioResponse:
    usuario = servicio.registrar(
        nombre_completo=datos.nombre_completo,
        email=datos.email,
        password_hash=obtener_password_hash(datos.password),
        rol=datos.rol,
    )
    return UsuarioResponse.model_validate(usuario)


@router.get(
    "",
    response_model=list[UsuarioResponse],
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)
def listar_usuarios(
    servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios),
) -> list[UsuarioResponse]:
    return [UsuarioResponse.model_validate(u) for u in servicio.listar_todos()]


@router.patch(
    "/{usuario_id}/rol",
    response_model=UsuarioResponse,
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)
def cambiar_rol(
    usuario_id: uuid.UUID,
    datos: CambiarRolRequest,
    servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios),
) -> UsuarioResponse:
    usuario = servicio.cambiar_rol(usuario_id, datos.nuevo_rol)
    return UsuarioResponse.model_validate(usuario)


@router.patch(
    "/{usuario_id}/activar",
    response_model=UsuarioResponse,
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)
def activar_usuario(
    usuario_id: uuid.UUID, servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios)
) -> UsuarioResponse:
    return UsuarioResponse.model_validate(servicio.activar(usuario_id))


@router.patch(
    "/{usuario_id}/desactivar",
    response_model=UsuarioResponse,
    dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))],
)
def desactivar_usuario(
    usuario_id: uuid.UUID, servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios)
) -> UsuarioResponse:
    return UsuarioResponse.model_validate(servicio.desactivar(usuario_id))
