# 14. Estándares de Python Moderno y Herramientas

El ecosistema de Python ha evolucionado sustancialmente. A continuación se detallan las mejores prácticas de tipado estático, gestión de dependencias con `uv` y empaquetado en contenedores Docker multi-stage.

---

## 1. Tipado Estático Moderno (Type Hints)

A partir de Python 3.10+, se deben preferir las construcciones nativas del lenguaje sobre importaciones redundantes de `typing`:

```python
# ❌ ESTILO ANTIGUO (Python < 3.9)
from typing import List, Dict, Optional, Union
def procesar(valores: List[str], config: Optional[Dict[str, Union[int, str]]]) -> None:
    pass

# ✅ ESTILO MODERNO (Python 3.10+)
def procesar(valores: list[str], config: dict[str, int | str] | None = None) -> None:
    pass
```

### Reglas de Tipado:
- Declarar el tipo de todos los argumentos y del retorno `-> Tipo` en métodos públicos.
- Usar identificadores universales seguros: `import uuid` y anotar con `uuid.UUID`.
- Usar enumeraciones (`enum.Enum`) para estados discretos y evitar strings "mágicos".

---

## 2. Gestión de Entornos y Dependencias con `uv`

En el curso se utiliza **`uv`**, la herramienta moderna y de altísimo rendimiento para entornos y paquetes en Python:

```bash
# Inicializar un proyecto
uv init

# Crear y activar el entorno virtual
uv venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Añadir dependencias al pyproject.toml y actualizar uv.lock
uv add "fastapi[standard]" pymongo

# Instalar dependencias exactas en CI/CD o producción
uv sync --frozen --no-dev

# Ejecutar comandos directamente en el entorno
uv run fastapi dev app/main.py
uv run python -m unittest discover
```

---

## 3. Contenedorización Multi-Stage con Docker

Para desplegar microservicios FastAPI de forma segura y liviana, se utiliza un Dockerfile multi-stage con cache de dependencias y usuario sin privilegios (*non-root*).

### Archivo: `Dockerfile`
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-slim AS build

# Copiar el binario ultra rápido de uv
COPY --from=ghcr.io/astral-sh/uv:0.8.21 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# 1. Instalar dependencias con caché para compilación rápida
COPY uv.lock pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

# 2. Copiar código fuente y sincronizar
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- ETAPA DE RUNTIME LIMPIA Y SEGURA ---
FROM python:3.13-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH"

# Usuario seguro no-root
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /app -s /bin/false appuser

WORKDIR /app
COPY --from=build --chown=appuser:appgroup /app .

USER appuser
EXPOSE 8000

ENTRYPOINT ["fastapi", "run", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Directivas para Agentes de IA

1. **Anotar siempre tipos en funciones nuevas**: Use `param: int | None = None` y retornos explícitos.
2. **Respetar el entorno uv**: No instruya al usuario a usar `pip install` cuando el proyecto contiene `uv.lock` y `pyproject.toml`. Indique `uv add`.
3. **No ejecutar contenedores como root**: Asegúrese de crear un usuario específico como `appuser` en imágenes Docker de producción.
