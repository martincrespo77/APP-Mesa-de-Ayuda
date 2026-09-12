# Mesa de Ayuda — Cooperativa Comunicarlos

Sistema de gestión de Mesa de Ayuda para una cooperativa de servicios (fibra
óptica, telefonía IP, TV), desarrollado como Proyecto Profesional (PP5) para
FIE. Permite a los usuarios de la cooperativa reportar **incidentes** (fallas
de servicio) y **solicitudes** (pedidos administrativos), y a supervisores,
operadores y técnicos gestionarlos a través de un ciclo de vida con estados y
permisos por rol.

## Arquitectura

El proyecto está organizado en tres capas independientes que se comunican
únicamente por HTTP/JSON, siguiendo un diseño de dominio rico (DDD-lite):

```
├── app/                  API REST (FastAPI)
│   ├── compartido/       Excepciones base de dominio
│   ├── usuarios/         Dominio, servicios, repositorio y router de Usuario
│   ├── requerimientos/   Dominio, servicios, repositorio y router de Requerimiento
│   │   └── dominio/      Requerimiento (base), Incidente, Solicitud, Estados
│   ├── notificaciones/   Observer: despacha eventos de dominio (auditoría/log)
│   ├── infraestructura/  Conexión a MongoDB, repositorios concretos (PyMongo)
│   ├── auth.py           JWT + bcrypt
│   ├── deps.py           Inyección de dependencias de FastAPI
│   ├── config.py         Configuración tipada (variables de entorno)
│   └── main.py           Punto de entrada de la API
├── desktop/              Cliente de escritorio (PyQt6), independiente de app/
│   ├── views/            LoginWindow, MainWindow
│   ├── api_client.py     ClienteApi (ABC): ApiClienteHttp / ApiClienteDemo
│   ├── models.py         DTOs propios del cliente (no reusa el dominio de app/)
│   └── main.py           Punto de entrada del cliente
├── web/                  Portal web (HTML/CSS/JS puro), montado como estáticos en app/main.py
│   ├── index.html        Login (JWT en localStorage)
│   ├── app.html          Portal: alta de ticket, listado y detalle
│   └── js/, css/         fetch a la API, sin frameworks ni build step
├── scripts/
│   └── seed_mongo.py     Script de siembra de datos de ejemplo en MongoDB
├── tests/                131 tests (pytest)
├── bruno/                Colección de requests HTTP (Bruno) para probar la API
├── Dockerfile            Imagen multi-stage de la API (uv + usuario no-root)
└── docker-compose.yml    Orquesta la API + MongoDB
```

### Patrones de diseño aplicados

- **Information Expert**: las entidades `Incidente`/`Solicitud` validan sus
  propias transiciones de estado y los permisos del actor que las invoca.
- **Factory Method**: `FabricaRequerimientos` crea y reconstruye Incidentes y
  Solicitudes según su tipo.
- **Observer**: `DespachadorEventos` notifica los eventos de dominio
  (creación, cambios de estado) a observadores desacoplados (`notificaciones/`).
- **Repository**: `RepositorioUsuarios`/`RepositorioRequerimientos` son
  interfaces abstractas; `app/infraestructura/` las implementa con PyMongo,
  y `tests/fakes.py` las implementa en memoria para los tests.

El cliente de escritorio (`desktop/`) no importa nada de `app/`: se comunica
exclusivamente por HTTP a través de `ClienteApi`, que tiene dos
implementaciones intercambiables:

- `ApiClienteHttp`: cliente real contra la API (usa `httpx`).
- `ApiClienteDemo`: dataset sintético en memoria, sin red ni backend
  (usado por el **Modo Demostración**, ver más abajo).

El portal web (`web/`) es igual de independiente: JavaScript puro que
consume la API vía `fetch`, servido como archivos estáticos por la misma
instancia de FastAPI (`app.mount("/", StaticFiles(...))` en `app/main.py`,
montado después de los routers de API para que estos resuelvan primero). Al
ser mismo origen que la API no necesita configurar CORS, y es accesible
desde el celular en la misma red sin nada adicional (ver
[Portal web](#portal-web-navegadorcelular) más abajo).

### Stack tecnológico

- **Backend**: Python 3.12, FastAPI, Pydantic v2, PyMongo, python-jose (JWT),
  bcrypt.
- **Cliente de escritorio**: PyQt6, httpx.
- **Portal web**: HTML5 + CSS + JavaScript vanilla (`fetch`), sin frameworks
  ni paso de build — servido como estáticos por la propia API.
- **Persistencia**: MongoDB 7.
- **Gestión de dependencias**: [uv](https://docs.astral.sh/uv/).
- **Testing**: pytest, mongomock (para tests de infraestructura sin Mongo real).
- **Calidad de código**: ruff (lint), mypy --strict.
- **Contenedores**: Docker / Docker Compose.
- **Pruebas de API**: [Bruno](https://www.usebruno.com/) (`bruno/`).

## Requisitos previos

- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado.
- Python 3.12 (uv lo resuelve automáticamente si no está instalado).
- Docker y Docker Compose (para levantar el entorno completo).
- Opcional: [Bruno](https://www.usebruno.com/) (app de escritorio o
  `npx @usebruno/cli`) para correr la colección de requests de `bruno/`.

## Puesta en marcha

### 1. Clonar e instalar dependencias

```bash
uv sync
```

Esto crea el entorno virtual (`.venv/`) e instala todas las dependencias
(incluidas las de desarrollo: pytest, ruff, mypy) según `uv.lock`.

### 2. Variables de entorno

Copiar el archivo de ejemplo y ajustar si hace falta:

```bash
cp .env.example .env
```

| Variable             | Descripción                                   | Valor por defecto |
|-----------------------|-----------------------------------------------|--------------------|
| `SECRET_KEY`          | Clave para firmar JWT (mínimo 32 caracteres)  | —                  |
| `ALGORITHM`           | Algoritmo de firma JWT                        | `HS256`            |
| `EXPIRACION_MINUTOS`  | Expiración del token JWT                      | `60`               |
| `MONGODB_URL`         | URL de conexión a MongoDB                     | —                  |
| `MONGODB_DB_NAME`     | Nombre de la base de datos                    | —                  |

`SECRET_KEY`, `MONGODB_URL` y `MONGODB_DB_NAME` son obligatorias: la app
falla rápido al arrancar si no están definidas.

### 3. Levantar el entorno con Docker (recomendado)

```bash
docker compose up --build
```

Esto levanta:

- `mongo`: MongoDB 7, con healthcheck (puerto `27017`).
- `api`: la API FastAPI, esperando a que `mongo` esté saludable antes de
  arrancar (puerto `8000`).

Verificar que la API responde:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

La documentación interactiva (Swagger) queda disponible en
`http://localhost:8000/docs`.

Para bajar el entorno:

```bash
docker compose down
```

### 3bis. Alternativa: correr la API en local (sin Docker)

Con un MongoDB accesible (local o remoto) y `.env` apuntando a él:

```bash
uv run uvicorn app.main:app --reload
```

## Poblar la base de datos (seed)

`scripts/seed_mongo.py` siembra datos de ejemplo directamente contra
MongoDB usando las entidades de dominio y los repositorios reales (no pega
a la API): 5 usuarios (uno por cada rol) y 8 requerimientos (Incidentes y
Solicitudes) cubriendo los distintos estados del ciclo de vida. Es
idempotente (usa ids deterministas).

Con el backend/Mongo ya levantado (Docker o local):

```bash
uv run python -m scripts.seed_mongo
```

Usuarios de ejemplo creados (contraseña `Seed1234!` para todos):

| Email                              | Rol         |
|------------------------------------|-------------|
| `sofia.jefa@comunicarlos.com.ar`  | Supervisor  |
| `rosa.molina@comunicarlos.com.ar` | Operador    |
| `ivan.rios@comunicarlos.com.ar`   | Técnico     |
| `lucia.gomez@comunicarlos.com`    | Solicitante |
| `marcos.diaz@comunicarlos.com`    | Solicitante |

Regla de negocio validada en el dominio (`Usuario`): Operador, Técnico y
Supervisor exigen un email `@comunicarlos.com.ar`; el Solicitante puede
usar cualquier email. Intentar crear o ascender a un rol operativo con un
email fuera de ese dominio lanza `EmailCorporativoRequeridoError` (400).

## Cliente de escritorio (PyQt6)

El cliente vive en `desktop/` y es independiente de la API: puede correrse
en **modo conectado** (contra una API real) o en **Modo Demostración**
(datos sintéticos en memoria, sin backend ni red).

### Modo conectado (real)

Requiere la API corriendo (Docker o local) y, opcionalmente, la base
poblada con el seed:

```bash
uv run python -m desktop.main
```

Por defecto apunta a `http://localhost:8000`; se puede cambiar con `--url`:

```bash
uv run python -m desktop.main --url http://localhost:8000
```

### Modo Demostración (`--demo`)

No requiere backend ni MongoDB — arranca con un dataset sintético en
memoria, ideal para mostrar la UI sin depender de infraestructura:

```bash
uv run python -m desktop.main --demo
```

## Portal web (navegador/celular)

Alternativa liviana al cliente de escritorio para que un **Solicitante**
cargue un Incidente/Solicitud y consulte el estado de sus tickets desde
cualquier navegador, sin instalar nada — pensado también para acceder desde
el celular. No expone las acciones de gestión de Operador/Técnico/
Supervisor (asignar técnico, iniciar análisis, resolver, etc.): esas quedan
reservadas al cliente de escritorio, siguiendo la matriz de roles del
backend.

Con la API corriendo (Docker o local, ver más arriba), abrir en el
navegador:

```
http://localhost:8000
```

Desde el celular (misma red Wi-Fi que la máquina donde corre la API),
reemplazar `localhost` por la IP de esa máquina en la red local, por
ejemplo:

```
http://192.168.0.10:8000
```

(la IP se puede obtener con `ipconfig` en Windows, buscando el adaptador de
red activo).

Credenciales de prueba (requiere haber corrido el
[seed](#poblar-la-base-de-datos-seed)):

| Email                           | Contraseña   | Rol         |
|----------------------------------|--------------|-------------|
| `lucia.gomez@comunicarlos.com`  | `Seed1234!`  | Solicitante |
| `marcos.diaz@comunicarlos.com`  | `Seed1234!`  | Solicitante |

Funcionalidad disponible:

- **Login**: guarda el JWT en `localStorage` del navegador; se limpia solo
  ante un token vencido o un 401 de la API.
- **Nuevo requerimiento**: formulario reactivo que alterna los campos según
  el tipo elegido (Incidente o Solicitud).
- **Mis requerimientos**: listado de los propios tickets con su estado, y
  un detalle con el historial de auditoría completo. Desde el detalle, el
  Solicitante puede **cancelar** un ticket propio mientras está `ABIERTO`
  o **confirmar el cierre** de uno `RESUELTO` — las únicas dos transiciones
  que el dominio le permite ejecutar a ese rol.

## Tests

Correr toda la suite (131 tests):

```bash
uv run pytest
```

Los tests de infraestructura (repositorios PyMongo) usan `mongomock`, y los
de routers de FastAPI inyectan repositorios falsos en memoria
(`tests/fakes.py`) vía `app.dependency_overrides` — ningún test requiere
una instancia real de MongoDB corriendo.

### Lint y tipado estático

```bash
uv run ruff check .
uv run mypy app/ desktop/
```

## Probar la API con Bruno

La carpeta `bruno/` contiene una colección de requests HTTP organizada por
dominio (`01-usuarios/`, `02-requerimientos/`), pensada para ejecutarse
contra los datos del seed. Ver [`bruno/README.md`](bruno/README.md) para el
detalle de cada flujo.

Con la API corriendo y la base poblada:

```bash
npx @usebruno/cli run bruno --env local
```

O abriendo la carpeta `bruno/` como colección en la app de escritorio de
Bruno.

> **Nota**: tanto el CLI como la app de Bruno persisten en
> `bruno/environments/local.bru` los tokens/ids generados en tiempo de
> ejecución. Si tras correr la colección ese archivo queda con esos valores
> en vez de las variables originales, restaurarlo antes de commitear con
> `git checkout -- bruno/environments/local.bru`.

## Documentación de referencia

La carpeta `CONTEXTO inicial/` contiene la especificación completa del
proyecto (arquitectura, dominio, buenas prácticas), organizada en documentos
cortos pensados para lectura progresiva por fase de trabajo — ver
`CONTEXTO inicial/00_INDICE_Y_GUIA_DE_LECTURA.md` como punto de entrada.
