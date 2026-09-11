# 🛠️ 01 — Stack Tecnológico del Proyecto

`[⬅️ Anterior: Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 02_OBJETIVO_Y_DOMINIO_NEGOCIO.md](02_OBJETIVO_Y_DOMINIO_NEGOCIO.md)`

---

## 1. Definición Formal del Stack

El proyecto implementa una arquitectura desacoplada y robusta utilizando las siguientes tecnologías:

| Capa / Componente | Tecnología | Versión / Detalle | Propósito |
|---|---|---|---|
| **Lenguaje Base** | **Python** | `>= 3.12` | Tipado estático moderno (`typing`, `type | None`), POO limpia. |
| **Backend / API** | **FastAPI** + **Uvicorn** | `fastapi>=0.110`, `uvicorn[standard]>=0.29` | API REST asíncrona, enrutamiento, validación y OpenAPI/Swagger (`/docs`). |
| **Validación y DTOs** | **Pydantic v2** | `pydantic[email]>=2.0`, `pydantic-settings>=2.0` | Schemas de request/response en presentación y tipado seguro de variables `.env`. |
| **Persistencia / BD** | **MongoDB** + **PyMongo** | `pymongo>=4.7` | Base de datos documental NoSQL. Se utiliza driver nativo sin ORM para evitar sobrecarga. |
| **Autenticación y Seguridad** | **JWT** + **Bcrypt** | `python-jose[cryptography]>=3.3`, `bcrypt>=4.0` | Autenticación stateless basada en tokens con claims de rol y hash seguro de contraseñas. |
| **Frontend / Cliente Desk** | **PyQt6** + **HTTPX** | `pyqt6>=6.6`, `httpx>=0.28` | Cliente nativo de escritorio con estilos QSS oscuros y consumo síncrono de la API REST. |
| **Testing** | **Pytest** + **Mongomock** | `pytest>=8.0`, `mongomock>=4.1` | Suite de pruebas unitarias puras y pruebas de integración emulando MongoDB en memoria. |
| **Calidad de Código** | **Ruff** + **Mypy** | `ruff>=0.16.6`, `mypy>=2.3.1` | Linter/formateador ultra rápido (PEP 8) y verificación estática de tipos estricta. |
| **Gestión de Entorno** | **`uv` (Astral)** | `uv` / `pyproject.toml` | Gestor de paquetes y dependencias determinista y ultrarrápido con lockfile (`uv.lock`). |
| **Contenedores y Despliegue** | **Docker** & **Compose** | Docker Engine ≥ 24, Compose ≥ 2.20 | Entornos reproducibles y aislados de servicios (`mongo` y `api`). |
| **Colección de Requests** | **Bruno** | `bruno/` (`.bru` files) | Cliente REST liviano cuyas colecciones se versionan en Git sin cuentas en la nube. |

---

## 2. Configuración en `pyproject.toml`

La configuración unificada del proyecto declara las dependencias principales y de desarrollo:

```toml
[project]
name = "mesa-de-ayuda-comunicarlos"
version = "0.1.0"
description = "Mesa de Ayuda - Cooperativa Comunicarlos - PP5"
requires-python = ">=3.12"
dependencies = [
    "pydantic[email]>=2.0",
    "pydantic-settings>=2.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "python-jose[cryptography]>=3.3",
    "bcrypt>=4.0",
    "pymongo>=4.7",
    "pyqt6>=6.6",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "httpx>=0.28",
    "mongomock>=4.1",
    "ruff>=0.16.6",
    "mypy>=2.3.1",
]
```

---

## 3. Justificación de Decisiones Técnicas

1. **Python 3.12 puro en Dominio**: Ninguna librería externa (ni Pydantic ni FastAPI) ingresa a la capa de dominio. Esto garantiza portabilidad total.
2. **PyMongo sin ORM/ODM**: Evita el acoplamiento rígido de librerías como Beanie o MongoEngine, permitiendo implementar el patrón repositorio con mapeos explícitos (diccionario BSON <-> entidad pura).
3. **`uv` frente a pip tradicional**: Tiempos de resolución casi instantáneos y lockfile (`uv.lock`) inmutable para reproducibilidad garantizada.
4. **PyQt6 desacoplado**: La UI no importa ningún módulo de `app/`. Se comunica exclusivamente por HTTP a través de un `ApiClient`, soportando además un Modo Demo offline.

---

`[⬅️ Anterior: Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 02_OBJETIVO_Y_DOMINIO_NEGOCIO.md](02_OBJETIVO_Y_DOMINIO_NEGOCIO.md)`
