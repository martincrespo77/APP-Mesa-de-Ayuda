"""Lifespan vacío para tests de routers (Paso 5).

El lifespan real de la app (`app/main.py`) abre una conexión a MongoDB.
Los tests de integración de routers sobreescriben los repositorios
concretos con `Fake*` vía `app.dependency_overrides`, así que nunca
necesitan esa conexión: sobreescribir también `app.router.lifespan_context`
con este no-op evita que `TestClient(app)` intente conectarse a un
MongoDB real (y se cuelgue si no hay ninguno corriendo).
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan_vacio(app: FastAPI) -> AsyncGenerator[None]:
    yield
