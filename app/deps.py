"""Inyección de dependencias de FastAPI: identidad, repositorios y roles.

Los repositorios concretos (PyMongo, Paso 5) se construyen sobre la base
de datos abierta en el lifespan de la app (`app/main.py`):
`_obtener_base_datos_mongo` la toma de `request.app.state.db`. Los tests
de integración de routers sobreescriben `obtener_repositorio_usuarios`/
`obtener_repositorio_requerimientos` con `app.dependency_overrides` + los
`Fake*` de `tests/fakes.py`, así que nunca necesitan una conexión real.
"""

from collections.abc import Callable
from typing import Any, cast

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pymongo.database import Database

from app.auth import TokenInvalidoError, decodificar_token
from app.compartido.dominio import RolUsuario
from app.infraestructura.repo_requerimientos import RepositorioRequerimientosMongo
from app.infraestructura.repo_usuarios import RepositorioUsuariosMongo
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


def _obtener_base_datos_mongo(request: Request) -> Database[dict[str, Any]]:
    """Recupera la base de datos abierta en el lifespan de la app.

    `app.state` es dinámico (no tipado por Starlette): el `cast` documenta
    la expectativa de que `app/main.py` la dejó ahí durante el lifespan.
    """
    return cast("Database[dict[str, Any]]", request.app.state.db)


def obtener_repositorio_usuarios(
    db: Database[dict[str, Any]] = Depends(_obtener_base_datos_mongo),
) -> RepositorioUsuarios:
    """Provee el repositorio concreto de usuarios (PyMongo)."""
    return RepositorioUsuariosMongo(db)


def obtener_repositorio_requerimientos(
    db: Database[dict[str, Any]] = Depends(_obtener_base_datos_mongo),
) -> RepositorioRequerimientos:
    """Provee el repositorio concreto de requerimientos (PyMongo)."""
    return RepositorioRequerimientosMongo(db)


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
