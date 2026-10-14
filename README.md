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
│   ├── compartido/       Excepciones base + tipos compartidos (RolUsuario, ServicioComunicarlos)
│   ├── usuarios/         Dominio, servicios, repositorio y router de Usuario
│   ├── requerimientos/   Dominio, servicios, repositorio y router de Requerimiento
│   │   └── dominio/      Requerimiento (base), Incidente, Solicitud, Comentario, Estados
│   ├── supervision/      Relación N:M Supervisor <-> Operador/Técnico
│   ├── notificaciones/   Entidad Notificacion + Observer (despacha eventos de dominio)
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
├── tests/                257 tests (pytest)
├── bruno/                Colección de requests HTTP (Bruno) para probar la API
├── Dockerfile            Imagen multi-stage de la API (uv + usuario no-root)
└── docker-compose.yml    Orquesta la API + MongoDB
```

### Patrones de diseño aplicados

- **Information Expert**: `Requerimiento` valida sus propias transiciones de
  estado y los permisos del actor que las invoca, incluidos los comentarios
  (`agregar_comentario`, con reapertura automática de un `RESUELTO`) y la
  derivación entre técnicos (`derivar_interconsulta`).
- **Factory Method**: `FabricaRequerimientos` crea y reconstruye Incidentes y
  Solicitudes según su tipo.
- **Observer**: `DespachadorEventos` notifica cada evento de dominio a los
  observadores suscriptos — `ObservadorLogger` (auditoría por log) y
  `ObservadorNotificacionesMongo` (genera una `Notificacion` real por cada
  supervisor de un Operador/Técnico que generó el evento).
- **Repository**: `RepositorioUsuarios`/`RepositorioRequerimientos`/
  `RepositorioSupervision`/`RepositorioNotificaciones` son interfaces
  abstractas; `app/infraestructura/` las implementa con PyMongo, y
  `tests/fakes.py` las implementa en memoria para los tests.

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
git clone https://github.com/martincrespo77/APP-Mesa-de-Ayuda.git
cd APP-Mesa-de-Ayuda
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

El `.env` se usa al correr la API, el seed o el cliente desde el host (`uv
run ...`); los valores de `.env.example` apuntan al MongoDB que expone
Docker Compose en `localhost:27017`. El contenedor `api` no lee el `.env`:
recibe sus variables desde `docker-compose.yml`.

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
a la API): 6 usuarios (al menos uno por cada rol, los Solicitantes con
`servicios_suscriptos`) y 8 requerimientos (Incidentes y Solicitudes)
cubriendo los distintos estados del ciclo de vida, más una relación de
supervisión y una notificación de ejemplo. Es idempotente (usa ids
deterministas).

Con el backend/Mongo ya levantado (Docker o local):

```bash
uv run python -m scripts.seed_mongo
# o, dentro del contenedor de la API:
docker compose exec api python -m scripts.seed_mongo
```

Usuarios de ejemplo creados (contraseña `Seed1234!` para todos):

| Email                               | Rol         |
|-------------------------------------|-------------|
| `sofia.jefa@comunicarlos.com.ar`   | Supervisor  |
| `rosa.molina@comunicarlos.com.ar`  | Operador    |
| `ivan.rios@comunicarlos.com.ar`    | Técnico     |
| `marta.suarez@comunicarlos.com.ar` | Técnico (sin tickets; destino para probar la derivación) |
| `lucia.gomez@comunicarlos.com`     | Solicitante |
| `marcos.diaz@comunicarlos.com`     | Solicitante |

Reglas de negocio validadas en el dominio (`Usuario`): Operador, Técnico y
Supervisor exigen un email `@comunicarlos.com.ar` (el Solicitante puede usar
cualquier email) y no tienen `servicios_suscriptos`; el Solicitante, al
revés, debe suscribirse a al menos uno de los servicios de la cooperativa
(`ServicioComunicarlos`: `TELEFONIA_CELULAR`, `INTERNET_BANDA_ANCHA`,
`TELEVISION`). Violar cualquiera de las dos lanza `EmailCorporativoRequeridoError`
o `SuscripcionRequeridaError` (400).

### Categorías de Incidente y Solicitud

- **Incidente**: `urgencia` (`CRITICO`/`IMPORTANTE`/`MENOR`), `categoria`
  (`SERVICIO_INACCESIBLE`/`BLOQUEO_SIM`/`PERDIDA_O_DESTRUCCION_DE_EQUIPO`) y
  `servicio` (`ServicioComunicarlos`), además de `pasos_reproduccion`.
- **Solicitud**: `categoria` (`ALTA_SERVICIO`/`BAJA_SERVICIO`) y `servicio`.

Un ticket admite **comentarios** de seguimiento (`POST
/requerimientos/{id}/comentarios`): Solicitante solo sobre lo propio,
Operador siempre, Técnico solo si es el asignado, Supervisor nunca. Un
comentario de Operador/Técnico sobre un `RESUELTO` lo reabre a
`EN_PROGRESO` (auditado como evento `REAPERTURA`, no como un estado nuevo).
El técnico asignado puede derivar el ticket a otro técnico (`POST
/requerimientos/{id}/derivar`, interconsulta) mientras está `EN_ANALISIS`
o `EN_PROGRESO`.

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

Interfaz web responsiva (`web/`) que implementa las **Fases 1 a 4**
(Solicitante, Operador, Técnico y Supervisor). Se adapta dinámicamente según el
rol del usuario autenticado, respetando la [Matriz de roles y permisos](#matriz-de-roles-y-permisos)
tanto en el filtrado de acciones de la interfaz como en las validaciones de
dominio en el backend. Puede utilizarse desde navegadores de escritorio o
dispositivos móviles.

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

Credenciales de prueba para cada rol (requiere haber corrido el
[seed](#poblar-la-base-de-datos-seed)):

| Email                               | Contraseña   | Rol         | Acceso en Portal Web |
|-------------------------------------|--------------|-------------|----------------------|
| `lucia.gomez@comunicarlos.com`     | `Seed1234!`  | Solicitante | Creación, mis tickets, seguimiento y cierre |
| `rosa.molina@comunicarlos.com.ar`  | `Seed1234!`  | Operador    | Bandeja global, asignación de técnicos, comentarios |
| `ivan.rios@comunicarlos.com.ar`    | `Seed1234!`  | Técnico     | Tickets asignados, análisis, progreso, derivación y resolución |
| `sofia.jefa@comunicarlos.com.ar`   | `Seed1234!`  | Supervisor  | Métricas globales, equipo supervisado, notificaciones y usuarios |

Funcionalidades disponibles por rol:

- **Autenticación (JWT)**: Login unificado que almacena el token en `localStorage`,
  gestionando la expiración y cierre de sesión de forma segura.
- **Solicitante (Fase 1)**: Formulario reactivo de Incidentes/Solicitudes filtrado
  automáticamente por sus servicios contratados (`servicios_suscriptos`); listado
  de tickets propios con auditoría; cancelación de tickets en `ABIERTO`, confirmación
  de cierre en `RESUELTO` y comentarios de seguimiento.
- **Operador (Fase 2)**: Bandeja completa de requerimientos con filtros multicriterio;
  asignación técnica inicial; cancelación; reapertura de requerimientos resueltos
  mediante comentarios.
- **Técnico (Fase 3)**: Vista de tickets propios asignados; transiciones de estado
  (`EN_ANALISIS`, `EN_PROGRESO`, `RESUELTO` con nota de resolución); derivación
  entre técnicos (interconsulta) y comentarios operativos.
- **Supervisor (Fase 4)**: Panel de métricas globales (tickets abiertos, en progreso,
  resueltos); administración de equipo supervisado; bandeja de notificaciones; y
  gestión integral de usuarios (creación con validación de email corporativo, cambio
  de rol y activación/desactivación).

## Supervisión y notificaciones

Un Supervisor administra qué Operadores y Técnicos audita (`POST/GET/DELETE
/supervisiones`, relación N:M) y gestiona las notificaciones generadas
automáticamente ante eventos auditables ejecutados por sus supervisados
(`GET /notificaciones`, `PATCH /notificaciones/{id}/leida`).

Esta capacidad está disponible tanto en el **Portal Web** (pestañas dedicadas
"Equipo supervisado" y "Notificaciones" para el rol Supervisor) como directamente
a través de la **API REST** (documentada en Swagger `/docs` y con casos de prueba
en las colecciones de Bruno: `bruno/03-supervision/` y `bruno/04-notificaciones/`).

## Tests

Correr toda la suite (257 tests):

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
dominio (`01-usuarios/`, `02-requerimientos/`, `03-supervision/`,
`04-notificaciones/`), pensada para ejecutarse contra los datos del seed.
Ver [`bruno/README.md`](bruno/README.md) para el detalle de cada flujo.

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

## Matriz de roles y permisos

El dominio valida cada operación según el rol del actor (`RolUsuario`); la
UI solo oculta lo que el backend rechazaría de todos modos.

| Acción / Operación          | Solicitante       | Operador | Técnico         | Supervisor |
|-----------------------------|:-----------------:|:--------:|:---------------:|:----------:|
| Crear requerimiento propio  | ✅                | ✅       | ✅              | ✅         |
| Ver todos los requerimientos| ❌ (solo propios) | ✅       | ✅              | ✅         |
| Asignar técnico al ticket   | ❌                | ✅       | ❌              | ✅         |
| Iniciar progreso del ticket | ❌                | ❌       | ✅ (si asignado)| ✅         |
| Marcar como RESUELTO        | ❌                | ❌       | ✅ (si asignado)| ✅         |
| Dar cierre de conformidad   | ✅ (propios)      | ✅       | ❌              | ✅         |
| Cancelar / Desestimar       | ✅ (si ABIERTO)   | ✅       | ❌              | ✅         |
| Agregar comentario          | ✅ (propios)      | ✅       | ✅ (si asignado)| ❌         |
| Derivar a otro técnico      | ❌                | ❌       | ✅ (si asignado)| ❌         |
| Administrar usuarios        | ❌                | ❌       | ❌              | ✅         |
| Administrar supervisiones   | ❌                | ❌       | ❌              | ✅         |
| Recibir notificaciones      | ❌                | ❌       | ❌              | ✅         |

## Documentación de arquitectura

Los diagramas oficiales viven en [`docs/diagramas/`](docs/diagramas/README.md)
(clases, casos de uso, flujo y secuencia, en Mermaid `.mmd` y visores HTML).
El punto de entrada es la suite unificada
[`docs/diagramas/diagrama_suite_unificada.html`](docs/diagramas/diagrama_suite_unificada.html),
que se abre directamente en el navegador.
