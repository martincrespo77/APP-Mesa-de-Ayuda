"""Punto de entrada de la API FastAPI: instancia la app y monta los routers."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.compartido.excepciones import DominioError
from app.errores import codigo_http_para
from app.usuarios.router import router as router_usuarios

app = FastAPI(title="Mesa de Ayuda - Cooperativa Comunicarlos")


@app.exception_handler(DominioError)
async def manejar_dominio_error(request: Request, exc: DominioError) -> JSONResponse:
    """Traduce cualquier excepción de dominio al código HTTP correspondiente."""
    return JSONResponse(status_code=codigo_http_para(exc), content={"detail": str(exc)})


@app.get("/health", tags=["salud"])
def verificar_salud() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router_usuarios)
