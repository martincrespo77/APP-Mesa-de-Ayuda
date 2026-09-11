"""Punto de entrada de la API FastAPI: instancia la app y monta los routers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.compartido.excepciones import DominioError
from app.config import get_settings
from app.errores import codigo_http_para
from app.infraestructura.database import crear_cliente_mongo, crear_indices, obtener_base_datos
from app.requerimientos.router import router as router_requerimientos
from app.usuarios.router import router as router_usuarios


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Abre la conexión a MongoDB al arrancar la app y la cierra al apagarla.

    `app.state.db` es lo que consume `app/deps.py` para construir los
    repositorios concretos en cada request.
    """
    settings = get_settings()
    cliente = crear_cliente_mongo(settings)
    db = obtener_base_datos(cliente, settings)
    crear_indices(db)
    app.state.db = db
    yield
    cliente.close()


app = FastAPI(title="Mesa de Ayuda - Cooperativa Comunicarlos", lifespan=lifespan)


@app.exception_handler(DominioError)
async def manejar_dominio_error(request: Request, exc: DominioError) -> JSONResponse:
    """Traduce cualquier excepción de dominio al código HTTP correspondiente."""
    return JSONResponse(status_code=codigo_http_para(exc), content={"detail": str(exc)})


@app.get("/health", tags=["salud"])
def verificar_salud() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router_usuarios)
app.include_router(router_requerimientos)
