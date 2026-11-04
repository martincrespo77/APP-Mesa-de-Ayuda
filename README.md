<p align="center">
  <img src="assets/logo.svg" alt="Mesa de Ayuda Comunicarlos" width="760">
</p>

# 🎧 Mesa de Ayuda — Cooperativa Comunicarlos

## Sistema de Gestión de Incidentes y Servicios (FIE PP5)

> **Sistema integral de Help Desk & IT Service Management para servicios de telecomunicaciones (Fibra Óptica, Telefonía IP, TV), construido con arquitectura de Modelo de Dominio Rico (DDD estricto), API REST FastAPI, clientes Web/Desktop y persistencia en MongoDB.**

**Descripción académica:** Proyecto Profesional (PP5) para la Facultad de Informática y Electrónica (FIE). Modela el ciclo de vida completo de atención técnica mediante una jerarquía polimórfica de usuarios (Solicitante, Operador, Técnico, Supervisor), doble despacho (*Double Dispatch*) entre tickets y actores, validación de suscripciones de telecomunicaciones, derivación entre técnicos (interconsulta), reapertura automática auditada y despacho de eventos en tiempo real mediante el patrón Observer.

> ℹ️ **Estado del Proyecto:** Prototipo funcional completo con **372 tests automatizados**, clientes Web y Desktop operativos, y suite de diagramas UML/arquitectura interactiva en [`docs/diagramas/`](docs/diagramas/README.md).

---

## ⚡ Features

| Feature / Módulo | Descripción Técnica | Estado |
|---|---|---|
| **Modelo de Dominio Rico (DDD)** | Cero dominio anémico: la lógica de negocio vive en las entidades de dominio y Value Objects, aplicando *Information Expert* y *Tell, Don't Ask* | ✅ Implementado |
| **Jerarquía Polimórfica de Usuarios** | `Usuario` (abstracta: menor privilegio) ➔ `Solicitante` / `Empleado` (abstracta) ➔ `Operador`, `Tecnico`, `Supervisor`, instanciados por `FabricaUsuarios` | ✅ Implementado |
| **Jerarquía de Requerimientos** | `Incidente` (urgencia, categoría, pasos de reproducción) y `Solicitud` (altas/bajas) instanciados por `FabricaRequerimientos` | ✅ Implementado |
| **Doble Despacho (*Double Dispatch*)** | `Requerimiento` consulta a `actor.puede_*(self)` y el actor consulta al ticket con `pertenece_a(self)` o `esta_asignado_a(self)` sin violar encapsulamiento | ✅ Implementado |
| **Value Objects Inmutables** | `Email` canónico (normalización y validación por construcción), eliminando `@staticmethod` repetitivos de las entidades | ✅ Implementado |
| **Servicios Anoréxicos (Thin Services)** | `ServicioRequerimientos` y `ServicioUsuarios` como orquestadores puros: solo recuperan, delegan en el dominio, persisten y despachan eventos | ✅ Implementado |
| **Seguridad por Capacidades** | En `app/deps.py` se utiliza `requerir_permiso(lambda u: u.puede_...())`, desacoplando la capa HTTP de enums o nombres de roles | ✅ Implementado |
| **Ciclo de Vida de Tickets** | `ABIERTO` ➔ `EN_ANALISIS` ➔ `EN_PROGRESO` ➔ `RESUELTO` ➔ `CERRADO` (cancelable a `CANCELADO`) | ✅ Implementado |
| **Reapertura Automática** | Comentar sobre un ticket `RESUELTO` (por Operador o Técnico) lo devuelve a `EN_PROGRESO` disparando el evento `REAPERTURA` | ✅ Implementado |
| **Derivación (Interconsulta)** | Un técnico asignado puede transferir el ticket a otro técnico activo especializado mientras esté `EN_ANALISIS` o `EN_PROGRESO` | ✅ Implementado |
| **Observer Event Bus** | `DespachadorEventos` notifica en tiempo real a `ObservadorLogger` y `ObservadorNotificacionesMongo` | ✅ Implementado |
| **Supervisión Activa N:M** | `Supervisor.supervisar(empleado)` valida que sea supervisable y `RelacionSupervision` genera la notificación de auditoría | ✅ Implementado |
| **Portal Web Responsive** | HTML5 + Vanilla CSS + Vanilla JS (`fetch`), servido estático sin frameworks ni build step | ✅ Fases 1 a 4 completas |
| **Cliente Escritorio PyQt6** | Cliente nativo con soporte de Modo Conectado (`ApiClienteHttp`) y Modo Demo (`ApiClienteDemo`) | ✅ Implementado |
| **Persistencia NoSQL** | Repositorios desacoplados con PyMongo sobre MongoDB 7 | ✅ Implementado |
| **Testing & Calidad** | 372 tests (pytest + mongomock + fakes en memoria), `mypy --strict`, `ruff` | ✅ 372 PASS / 0 FAIL |
| **Suite de Diagramas** | Visor HTML interactivo unificado (Casos de Uso, Clases, Flujo y Secuencia) con compilador local | ✅ [`docs/diagramas/`](docs/diagramas/README.md) |

---

## 🏗️ Architecture

<p align="center">
  <img src="assets/architecture.svg" alt="Mesa de Ayuda - Arquitectura del Sistema" width="760">
</p>

```
[ Portal Web (web/) ]        [ Cliente Desktop PyQt6 (desktop/) ]
         │                                    │
         └───────────────┬────────────────────┘
                         │ (HTTP / JSON REST)
                         ▼
┌────────────────────────────────────────────────────────┐
│ FastAPI API Gateway + Auth Guard (JWT Bearer + bcrypt) │
│ Dependencias por capacidades: `requerir_permiso(...)`  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│             SERVICIOS DE APLICACIÓN (Orquestación Pura)│
│    `ServicioRequerimientos`, `ServicioUsuarios`, etc.  │
│    (Cero condicionales `if` de negocio o sobre roles)  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│                 DOMINIO RICO (DDD Estricto)            │
│                                                        │
│  FabricaRequerimientos ──► Incidente / Solicitud       │
│  FabricaUsuarios ────────► Solicitante / Empleados     │
│  Requerimiento ◄──(Double Dispatch)──► Usuario         │
│  Value Objects ──────────► Email, Comentario, Evento   │
└──────────────┬──────────────────────────┬──────────────┘
               │ (Eventos)                │ (Repositorios)
               ▼                          ▼
┌─────────────────────────────┐  ┌───────────────────────┐
│ DespachadorEventos Observer │  │ Puertos / Repositorio │
│ ├─► ObservadorLogger        │  │          │            │
│ └─► Notificaciones a Jefes  │  │ Adaptadores PyMongo   │
└─────────────────────────────┘  └──────────┬────────────┘
                                            │
                                            ▼
                                  [ MongoDB 7 Engine ]
```

### Principios y Patrones de Diseño Aplicados

- **Information Expert & Tell, Don't Ask**: Las entidades validan sus transiciones sin exponer atributos internos. Nadie le pregunta el rol al usuario para decidir por él: se le pregunta a la entidad `actor.puede_*(self)` y cada clase contesta polimórficamente.
- **Double Dispatch (Doble Despacho)**: `Requerimiento` recibe la entidad `actor: Usuario` completa y le consulta si tiene permiso para la acción. El actor le consulta al ticket si le pertenece o si lo tiene asignado (`pertenece_a(self)` / `esta_asignado_a(self)`).
- **Factory Method**: `FabricaRequerimientos` centraliza la creación polimórfica de `Incidente` y `Solicitud`. `FabricaUsuarios` es el **único lugar del sistema** donde un valor de `RolUsuario` se mapea a su clase concreta correspondiente.
- **Value Objects Inmutables**: Conceptos atómicos con formato propio como `Email` se modelan como Value Objects (`app/usuarios/dominio/email.py`), garantizando normalización (minúsculas, sin espacios) y validez por construcción sin necesidad de métodos estáticos.
- **Servicios de Aplicación Anoréxicos**: Los servicios en `app/*/servicios.py` actúan exclusivamente como coordinadores (recuperan entidades del repositorio, invocan la transición de dominio, persisten y despachan eventos). Prohibido validar roles o reglas de negocio dentro de los servicios.
- **Observer**: `DespachadorEventos` desacopla las consecuencias secundarias de los cambios de estado. `ObservadorLogger` genera trazas de auditoría y `ObservadorNotificacionesMongo` crea alertas persistidas para los supervisores a cargo del operador o técnico involucrado.
- **Repository & Dependency Inversion**: Los servicios operan contra interfaces abstractas (`RepositorioUsuarios`, `RepositorioRequerimientos`, `RepositorioSupervision`, `RepositorioNotificaciones`). En runtime se usan adaptadores PyMongo, y en pruebas se inyectan fakes en memoria (`tests/fakes.py`), permitiendo ejecutar los **372 tests en segundos**.

Detalle de diagramas UML interactivos: [`docs/diagramas/README.md`](docs/diagramas/README.md)

---

## ⚖️ Matriz de Roles y Capacidades Polimórficas

El sistema implementa una jerarquía polimórfica estricta donde cada clase concreta sobrescribe las capacidades que le corresponden:

| Acción / Capacidad | Solicitante | Operador | Técnico | Supervisor |
|---|:---:|:---:|:---:|:---:|
| Crear requerimiento propio | ✅ | ✅ | ✅ | ✅ |
| Ver todos los requerimientos | ❌ *(solo propios)* | ✅ | ✅ | ✅ |
| Asignar técnico al ticket | ❌ | ✅ | ❌ | ✅ |
| Iniciar progreso del ticket | ❌ | ❌ | ✅ *(si asignado)* | ✅ |
| Marcar como RESUELTO | ❌ | ❌ | ✅ *(si asignado)* | ✅ |
| Dar cierre de conformidad | ✅ *(propios)* | ✅ | ❌ | ✅ |
| Cancelar / Desestimar | ✅ *(si ABIERTO)* | ✅ | ❌ | ✅ |
| Agregar comentario | ✅ *(propios)* | ✅ | ✅ *(si asignado)* | ❌ |
| Derivar a otro técnico | ❌ | ❌ | ✅ *(si asignado)* | ❌ |
| Administrar usuarios | ❌ | ❌ | ❌ | ✅ |
| Administrar supervisiones | ❌ | ❌ | ❌ | ✅ |
| Recibir notificaciones | ❌ | ❌ | ❌ | ✅ |

### Reglas Críticas del Ciclo de Vida:
1. `ABIERTO` solo puede pasar a `EN_ANALISIS` (por Operador/Supervisor) o `CANCELADO`.
2. `EN_ANALISIS` requiere que haya un técnico asignado para poder transicionar a `EN_PROGRESO`.
3. `EN_PROGRESO` solo pasa a `RESUELTO` mediante una **nota de resolución técnica descriptiva**.
4. **Reapertura automática:** Si un Operador o Técnico comenta sobre un ticket `RESUELTO`, este vuelve automáticamente a `EN_PROGRESO` (evento `REAPERTURA`).
5. **Derivación (Interconsulta):** Solo el Técnico actualmente asignado puede derivar el ticket a otro Técnico activo (`POST /requerimientos/{id}/derivar`) mientras el estado sea `EN_ANALISIS` o `EN_PROGRESO`.

---

## 📂 Repository Structure

```
APP-Mesa-de-Ayuda/
├── README.md                   # Documentación principal del repositorio
├── AGENTS.md                   # Invariantes universales de Dominio Rico para agentes de IA
├── GEMINI.md                   # Directrices específicas de diseño para Gemini / Antigravity
├── CLAUDE.md                   # Directrices específicas de diseño para Claude Code
├── cambios corregidos.md       # Guía pedagógica en 20 partes para NotebookLM
├── pyproject.toml · uv.lock    # Gestión determinista de dependencias con uv
├── Dockerfile                  # Imagen multi-stage (uv + non-root user)
├── docker-compose.yml          # Orquestación de API FastAPI + MongoDB 7
├── assets/                     # Recursos gráficos vectoriales (logo.svg, architecture.svg)
├── app/                        # Backend REST API (FastAPI + Dominio Rico)
│   ├── main.py                 # Punto de entrada de la API y montaje de estáticos
│   ├── config.py               # Variables de entorno tipadas con Pydantic
│   ├── auth.py                 # Seguridad: hashing bcrypt y tokens JWT
│   ├── deps.py                 # Inyección de dependencias y seguridad por capacidades
│   ├── errores.py              # Manejo centralizado de excepciones de dominio
│   ├── compartido/             # Shared Kernel: tipos y validaciones de formato puras
│   │   ├── dominio.py          # Enums RolUsuario y ServicioComunicarlos
│   │   └── validaciones.py     # Funciones puras (texto_obligatorio, instancia_de)
│   ├── usuarios/               # Módulo de usuarios y autenticación
│   │   ├── dominio/            # Subpaquete polimórfico (una clase por rol + fábrica + Email)
│   │   ├── repositorio.py      # Interfaz abstracta RepositorioUsuarios
│   │   ├── servicios.py        # ServicioUsuarios (orquestación pura)
│   │   └── router.py           # Endpoints FastAPI para gestión y login
│   ├── requerimientos/         # Módulo de incidentes y solicitudes
│   │   ├── dominio/            # Subpaquete: Requerimiento, Incidente, Solicitud, Estados
│   │   ├── fabrica.py          # FabricaRequerimientos (Factory Method)
│   │   ├── repositorio.py      # Interfaz abstracta RepositorioRequerimientos
│   │   ├── servicios.py        # ServicioRequerimientos (orquestación pura)
│   │   └── router.py           # Endpoints FastAPI de ciclo de vida
│   ├── supervision/            # Entidad RelacionSupervision y servicio de auditoría
│   ├── notificaciones/         # Entidad Notificación persistida + Observer Event Bus
│   └── infraestructura/        # Conexión a MongoDB y repositorios PyMongo
├── desktop/                    # Cliente de escritorio desacoplado (PyQt6)
│   ├── main.py                 # Punto de entrada del cliente desktop
│   ├── api_client.py           # ClienteApi (ABC): ApiClienteHttp / ApiClienteDemo
│   ├── models.py               # DTOs propios del cliente desktop
│   └── views/                  # Vistas: LoginWindow, MainWindow
├── web/                        # Portal Web Responsive (HTML5 / Vanilla CSS / JS)
│   ├── index.html              # Login unificado con JWT en localStorage
│   ├── app.html                # Portal dinámico según rol (Fases 1 a 4)
│   ├── css/                    # Estilos CSS responsivos (móvil y escritorio)
│   └── js/                     # Lógica cliente (fetch a la API, sin frameworks)
├── docs/                       # Documentación técnica
│   └── diagramas/              # Suite interactiva (.html), fuentes (.mmd) y compilador
├── scripts/
│   └── seed_mongo.py           # Script idempotente de siembra de datos de prueba
├── bruno/                      # Colección completa de peticiones HTTP (Bruno)
└── tests/                      # Suite de 372 pruebas unitarias y de integración
```

---

## 🚀 Puesta en Marcha

### Requisitos Previos
- [uv](https://docs.astral.sh/uv/getting-started/installation/) instalado (o Python 3.12).
- Docker y Docker Compose (recomendado para ejecución integrada).

### 1. Clonar e Instalar Dependencias

```bash
git clone https://github.com/martincrespo77/APP-Mesa-de-Ayuda.git
cd APP-Mesa-de-Ayuda
uv sync
```

### 2. Configuración de Entorno

Copiar el archivo de plantilla:

```bash
cp .env.example .env
```

| Variable | Descripción | Valor por Defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta para firma criptográfica JWT | — *(Obligatoria)* |
| `ALGORITHM` | Algoritmo de firma de tokens | `HS256` |
| `EXPIRACION_MINUTOS` | Tiempo de vida del access token | `60` |
| `MONGODB_URL` | String de conexión a MongoDB | `mongodb://localhost:27017` |
| `MONGODB_DB_NAME` | Nombre de la base de datos | `mesa_de_ayuda` |

### 3. Levantar con Docker Compose (Recomendado)

```bash
docker compose up -d --build
```

Esto inicia:
- **MongoDB 7 (`mongo`)**: Puerto `27017` con healthcheck.
- **API FastAPI (`api`)**: Puerto `8000`, esperando la disponibilidad de la base de datos.

Verificar el estado del servicio:
```bash
curl http://localhost:8000/health
# {"status":"ok"}
```
Documentación interactiva Swagger: `http://localhost:8000/docs`

---

## 🧪 Datos de Prueba (Seed)

El script `scripts/seed_mongo.py` puebla MongoDB de forma idempotente con usuarios de cada rol, tickets en distintos estados y relaciones de supervisión:

```bash
# Desde el host con uv:
uv run python -m scripts.seed_mongo

# O dentro del contenedor Docker:
docker compose exec api python -m scripts.seed_mongo
```

### Credenciales de Acceso Universal (`Seed1234!`):

| Rol | Email | Propósito / Alcance |
|---|---|---|
| 👑 **Supervisor** | `sofia.jefa@comunicarlos.com.ar` | Métricas globales, supervisión N:M, notificaciones y usuarios |
| 🎧 **Operador** | `rosa.molina@comunicarlos.com.ar` | Bandeja general, triage, asignación de técnicos y comentarios |
| 🔧 **Técnico** | `ivan.rios@comunicarlos.com.ar` | Tickets asignados, diagnóstico, derivación y resolución |
| 🔧 **Técnico 2** | `marta.suarez@comunicarlos.com.ar` | Técnico de destino para probar la interconsulta/derivación |
| 👤 **Solicitante** | `lucia.gomez@comunicarlos.com` | Solicitante con abono a Fibra Óptica, TV y Telefonía |
| 👤 **Solicitante** | `marcos.diaz@comunicarlos.com` | Solicitante con abono a Internet Banda Ancha |

---

## 💻 Clientes de Acceso

### 1. Portal Web (Navegador y Móvil)
El portal web (`web/`) está optimizado para dispositivos móviles y de escritorio. Al estar servido por FastAPI, no requiere configurar CORS:

- **Desde la PC:** `http://localhost:8000`
- **Desde el Celular (misma red Wi-Fi o Tailscale):** `http://<IP_LOCAL>:8000`

### 2. Cliente de Escritorio (PyQt6)
Ubicado en `desktop/`, se comunica con la API vía HTTP y cuenta con dos modalidades:

```bash
# Modo Conectado (requiere API levantada):
uv run python -m desktop.main --url http://localhost:8000

# Modo Demostración (100% offline, datos en memoria):
uv run python -m desktop.main --demo
```

---

## 🔍 Verificación, Calidad y Tests

Ejecución de la suite completa de **372 pruebas automatizadas**:

```bash
# Tests unitarios y de integración:
uv run pytest

# Verificación de formato y linter:
uv run ruff check app scripts docs

# Tipado estático estricto:
uv run mypy app scripts
```

### Pruebas de API con Bruno
En la carpeta `bruno/` se encuentra la colección para ejecutar flujos de prueba automatizados:

```bash
npx @usebruno/cli run bruno --env local
```

---

## 📊 Documentación de Arquitectura

El sistema incluye una suite de diagramas UML interactivos en [`docs/diagramas/`](docs/diagramas/README.md), compilados con [`compilar_mermaid.py`](docs/diagramas/compilar_mermaid.py).

Para visualizar la arquitectura completa con soporte de filtrado y simulación de escenarios, abre directamente en tu navegador:
👉 **[`docs/diagramas/diagrama_suite_unificada.html`](docs/diagramas/diagrama_suite_unificada.html)**
