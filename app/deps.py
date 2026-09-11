"""Inyección de dependencias de FastAPI: identidad, repositorios y roles.

Los proveedores de repositorio concreto (`obtener_repositorio_usuarios`,
`obtener_repositorio_requerimientos`) quedan con `NotImplementedError`
hasta el Paso 5 (PyMongo). FastAPI no ejecuta `Depends()` al iniciar la
app, así que Swagger renderiza igual; los tests de integración de routers
los sobreescriben con `app.dependency_overrides` + los `Fake*` de
`tests/fakes.py`.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.auth import TokenInvalidoError, decodificar_token
from app.compartido.dominio import RolUsuario
from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.observador_logger import ObservadorLogger
from app.requerimientos.repositorio import RepositorioRequerimientos
from app.requerimientos.servicios import ServicioRequerimientos
from app.usuarios.dominio import Usuario
from app.usuarios.repositorio import RepositorioUsuarios
from app.usuarios.servicios import ServicioUsuarios

_esquema_oauth2 = OAuth2PasswordBearer(tokenUrl="/usuarios/login")

# El despachador de eventos no persiste nada: puede vivir ya como singleton
# de proceso, con el único observador de dominio (ObservadorLogger)
# suscripto. Observadores con infraestructura externa se agregan en el
# Paso 5 sin tocar esta función.
_despachador_eventos = DespachadorEventos()
_despachador_eventos.suscribir(ObservadorLogger())


def obtener_repositorio_usuarios() -> RepositorioUsuarios:
    """Provee el repositorio concreto de usuarios (PyMongo, Paso 5)."""
    raise NotImplementedError(
        "RepositorioUsuarios concreto pendiente del Paso 5 (PyMongo). "
        "En tests, sobreescribir con app.dependency_overrides + FakeRepositorioUsuarios."
    )


def obtener_repositorio_requerimientos() -> RepositorioRequerimientos:
    """Provee el repositorio concreto de requerimientos (PyMongo, Paso 5)."""
    raise NotImplementedError(
        "RepositorioRequerimientos concreto pendiente del Paso 5 (PyMongo). "
        "En tests, sobreescribir con app.dependency_overrides + FakeRepositorioRequerimientos."
    )


def obtener_despachador_eventos() -> DespachadorEventos:
    """Provee el despachador de eventos (Observer) del proceso."""
    return _despachador_eventos


def obtener_servicio_usuarios(
    repositorio: RepositorioUsuarios = Depends(obtener_repositorio_usuarios),
) -> ServicioUsuarios:
    return ServicioUsuarios(repositorio)


def obtener_servicio_requerimientos(
    repositorio: RepositorioRequerimientos = Depends(obtener_repositorio_requerimientos),
    despachador: DespachadorEventos = Depends(obtener_despachador_eventos),
) -> ServicioRequerimientos:
    return ServicioRequerimientos(repositorio, despachador)


def obtener_usuario_actual(
    token: str = Depends(_esquema_oauth2),
    servicio: ServicioUsuarios = Depends(obtener_servicio_usuarios),
) -> Usuario:
    """Decodifica el token y recarga al usuario desde el repositorio.

    Recargar en cada request (en vez de confiar ciegamente en los claims
    del JWT) permite que desactivar a un usuario surta efecto de inmediato,
    sin esperar a que su token expire.
    """
    try:
        usuario_id, _rol_del_token = decodificar_token(token)
    except TokenInvalidoError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o expiradas.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    usuario = servicio.obtener_por_id(usuario_id)
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario no existe o fue desactivado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return usuario


def requerir_rol(*roles_permitidos: RolUsuario) -> Callable[[Usuario], Usuario]:
    """Dependencia-fábrica: exige que el rol del usuario actual esté autorizado.

    Uso exclusivo en endpoints SIN contraparte de dominio (ej. administrar
    usuarios, matriz de doc02: solo `SUPERVISOR`). Las transiciones de
    `Requerimiento` no la usan: el propio método de la entidad ya valida
    el rol (Information Expert) y lanza `PermisoDenegadoError`, traducido a
    HTTP 403 por el exception handler — duplicar el chequeo aquí sería
    repetir la misma regla de negocio en dos capas.
    """

    def verificar(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if usuario_actual.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{usuario_actual.rol.value}' no tiene acceso a esta operación.",
            )
        return usuario_actual

    return verificar
