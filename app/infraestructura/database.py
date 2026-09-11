"""Conexión a MongoDB y creación de índices (Paso 5).

`MongoClient` administra su propio pool de conexiones: se crea una única
vez en el lifespan de FastAPI (`app/main.py`) y se cierra al apagar la app.
Los tests de integración (`tests/test_infraestructura.py`) usan
`mongomock.MongoClient()` en su lugar y no pasan por `crear_cliente_mongo`.

El id de dominio (UUID en formato string) se usa directamente como `_id` de
Mongo en ambas colecciones (ver `repo_usuarios.py`/`repo_requerimientos.py`),
así que ya queda cubierto por el índice único que Mongo crea por defecto
sobre `_id`; `crear_indices` solo agrega los índices adicionales que
documenta `06_INFRAESTRUCTURA_Y_PERSISTENCIA.md`.
"""

from typing import Any

from pymongo import MongoClient
from pymongo.database import Database

from app.config import Settings

COLECCION_USUARIOS = "usuarios"
COLECCION_REQUERIMIENTOS = "requerimientos"


def crear_cliente_mongo(settings: Settings) -> MongoClient[dict[str, Any]]:
    """Instancia el `MongoClient` con la URL configurada.

    PyMongo es perezoso: instanciar el cliente no abre una conexión de red
    por sí solo, eso ocurre recién en la primera operación real (aquí,
    dentro de `crear_indices`).
    """
    return MongoClient(settings.MONGODB_URL)


def obtener_base_datos(
    cliente: MongoClient[dict[str, Any]], settings: Settings
) -> Database[dict[str, Any]]:
    """Selecciona la base de datos configurada (`MONGODB_DB_NAME`)."""
    return cliente[settings.MONGODB_DB_NAME]


def crear_indices(db: Database[dict[str, Any]]) -> None:
    """Crea los índices críticos de la tabla de colecciones (idempotente).

    `create_index` no falla si el índice ya existe: es seguro llamarla en
    cada arranque de la app.
    """
    db[COLECCION_USUARIOS].create_index("email", unique=True)
    db[COLECCION_REQUERIMIENTOS].create_index("solicitante_id")
    db[COLECCION_REQUERIMIENTOS].create_index("estado")
    db[COLECCION_REQUERIMIENTOS].create_index("tipo")
