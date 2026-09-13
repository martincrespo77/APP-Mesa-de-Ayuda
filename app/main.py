"""Punto de entrada de la API FastAPI: instancia la app y monta los routers."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.compartido.excepciones import DominioError
from app.config import get_settings
from app.errores import codigo_http_para
from app.infraestructura.database import crear_cliente_mongo, crear_indices, obtener_base_datos
from app.notificaciones.router import router as router_notificaciones
from app.requerimientos.router import router as router_requerimientos
from app.supervision.router import router as router_supervision
from app.usuarios.router import router as router_usuarios

# Sin esto, `ObservadorLogger` (Paso 3, app/notificaciones/observador_logger.py)
# escribe a un logger ("mesa_de_ayuda.auditoria") sin ningún handler
# configurado en ningún lado de la app: sus mensajes INFO se descartan en
# silencio en cualquier corrida real (local o Docker) — solo "funcionan"
# en los tests porque `caplog` de pytest los captura sin necesitar handler.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


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
app.include_router(router_supervision)
app.include_router(router_notificaciones)

# Montado al final y en la raíz ("/"): las rutas de API ya registradas arriba
# siguen resolviendo primero (FastAPI matchea en orden de registro), así que
# este mount solo captura lo que ningún router respondió (el portal web
# estático). Mismo origen que la API => sin necesidad de CORS, ni desde el
# celular en la red local.
app.mount("/", StaticFiles(directory="web", html=True), name="web")
