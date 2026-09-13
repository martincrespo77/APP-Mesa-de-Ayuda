"""Mapeo de excepciones de dominio (`DominioError`) a códigos de estado HTTP.

Centraliza la traducción en un único lugar en vez de repetir `try/except`
en cada endpoint: los routers dejan que la excepción de dominio suba tal
cual y el `exception_handler` de `app/main.py` la traduce usando
`codigo_http_para`.
"""

from fastapi import status

from app.compartido.excepciones import DominioError
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    RequerimientoNoEncontradoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)
from app.usuarios.excepciones import (
    CredencialesInvalidasError,
    EmailYaRegistradoError,
    UsuarioNoEncontradoError,
    UsuarioYaActivoError,
    UsuarioYaInactivoError,
)

_CODIGOS_HTTP: dict[type[DominioError], int] = {
    PermisoDenegadoError: status.HTTP_403_FORBIDDEN,
    RequerimientoNoEncontradoError: status.HTTP_404_NOT_FOUND,
    UsuarioNoEncontradoError: status.HTTP_404_NOT_FOUND,
    TransicionInvalidaError: status.HTTP_409_CONFLICT,
    TecnicoNoAsignadoError: status.HTTP_409_CONFLICT,
    NotaResolucionRequeridaError: status.HTTP_409_CONFLICT,
    EmailYaRegistradoError: status.HTTP_409_CONFLICT,
    UsuarioYaActivoError: status.HTTP_409_CONFLICT,
    UsuarioYaInactivoError: status.HTTP_409_CONFLICT,
    CredencialesInvalidasError: status.HTTP_401_UNAUTHORIZED,
}


def codigo_http_para(error: DominioError) -> int:
    """Código HTTP para el tipo exacto de `error`, heredando de su MRO si falta.

    Una subclase de `RequerimientoError`/`UsuarioError` sin código explícito
    cae en 400 Bad Request (no en un 500 de error no controlado).
    """
    for clase in type(error).__mro__:
        if clase in _CODIGOS_HTTP:
            return _CODIGOS_HTTP[clase]
    return status.HTTP_400_BAD_REQUEST
