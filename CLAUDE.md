# Guía para Claude Code — Mesa de Ayuda (Comunicarlos)

Este archivo proporciona el contexto arquitectónico, reglas de negocio y directrices de implementación para que **Claude Code** trabaje de forma prolija, segura y consistente en este repositorio.

---

## 🏛️ Arquitectura del Proyecto

- **Backend (`app/`)**: API REST construida con Python 3.12 y FastAPI.
  - Diseño DDD-lite: La lógica de negocio y las validaciones viven en las entidades de dominio (`app/requerimientos/dominio/`, `app/usuarios/dominio/`, etc.), no en los endpoints ni en la base de datos.
  - Patrones aplicados: **Information Expert** (las entidades validan sus transiciones), **Factory Method** (construcción polimórfica de Incidentes y Solicitudes), **Observer** (`DespachadorEventos` despacha eventos a `ObservadorLogger` y `ObservadorNotificacionesMongo`).
  - Base de Datos: MongoDB 7 mediante PyMongo.
- **Portal Web (`web/`)**: HTML5, Vanilla CSS responsivo y Vanilla JavaScript moderno (`fetch`).
  - **Sin frameworks ni paso de build**: No uses React, Vue, Vite ni Node.js.
  - Servido directamente como archivos estáticos por FastAPI (`app.mount("/", StaticFiles(directory="web", html=True))`).
  - Mismo origen HTTP/JSON: No requiere configuración de CORS.
- **Cliente Escritorio (`desktop/`)**: Cliente PyQt6 independiente que consume la API.
- **Contenedores**: Docker y Docker Compose (`docker-compose.yml`).

---

## ⚖️ Matriz de Roles y Reglas de Negocio Inmutables

El sistema cuenta con 4 roles estrictos (`RolUsuario`):

| Acción / Operación | Solicitante | Operador | Técnico | Supervisor |
|---|:---:|:---:|:---:|:---:|
| Crear requerimiento propio | ✅ | ✅ | ✅ | ✅ |
| Ver todos los requerimientos | ❌ (solo propios) | ✅ | ✅ | ✅ |
| Asignar técnico al ticket | ❌ | ✅ | ❌ | ✅ |
| Iniciar progreso del ticket | ❌ | ❌ | ✅ (si asignado) | ✅ |
| Marcar como RESUELTO | ❌ | ❌ | ✅ (si asignado) | ✅ |
| Dar cierre de conformidad | ✅ (propios) | ✅ | ❌ | ✅ |
| Cancelar / Desestimar | ✅ (si ABIERTO) | ✅ | ❌ | ✅ |
| Agregar comentario | ✅ (propios) | ✅ | ✅ (si asignado) | ❌ |
| Derivar a otro técnico | ❌ | ❌ | ✅ (si asignado) | ❌ |
| Administrar usuarios | ❌ | ❌ | ❌ | ✅ |
| Administrar supervisiones | ❌ | ❌ | ❌ | ✅ |
| Recibir notificaciones | ❌ | ❌ | ❌ | ✅ |

### Reglas Críticas del Ciclo de Vida:
1. `ABIERTO` solo puede pasar a `EN_ANALISIS` (por Operador/Supervisor) o `CANCELADO`.
2. `EN_ANALISIS` requiere que haya un técnico asignado para poder pasar a `EN_PROGRESO`.
3. `EN_PROGRESO` solo puede pasar a `RESUELTO` mediante una nota de resolución técnica descriptiva.
4. **Reapertura:** Si un Operador o Técnico comenta sobre un ticket `RESUELTO`, este vuelve automáticamente a `EN_PROGRESO` (evento `REAPERTURA`).
5. **Derivación (Interconsulta):** Solo el Técnico actualmente asignado puede derivar el ticket a otro Técnico (`POST /requerimientos/{id}/derivar`) mientras el estado sea `EN_ANALISIS` o `EN_PROGRESO`.

---

## 🎯 Plan de Trabajo Activo: `PLAN_DESARROLLO_4_ROLES.md`

El usuario solicitó construir la interfaz web adaptada a los 4 roles de forma **modular, prolija y paso a paso**:

- **Fase 1:** Rol Solicitante (optimización de autoservicio y filtros de servicios contratados).
- **Fase 2:** Rol Operador (bandeja general, triage, iniciar análisis, asignación de técnicos con dropdown y comentarios).
- **Fase 3:** Rol Técnico (mis asignaciones, iniciar progreso, derivación/interconsulta y resolución con nota).
- **Fase 4:** Rol Supervisor (panel de métricas, bandeja de notificaciones en tiempo real y administración de supervisados).

> [!IMPORTANT]
> Al trabajar en una fase, **no modifiques las otras fases prematuramente**. Completa una fase, pruébala y permite que el usuario la valide en su navegador/celular antes de continuar.

---

## 🛠️ Comandos de Entorno y Verificación

- **Docker Compose (corriendo en el sistema):**
  ```bash
  docker compose ps
  docker compose logs -f api
  docker compose restart api
  ```
- **Firewall Tailscale (acceso celular `100.109.79.72`):**
  ```bash
  sudo ./scripts/firewall_tailscale.sh status
  ```
- **Poblar / Restaurar datos de prueba (Seed):**
  ```bash
  docker compose exec api python -m scripts.seed_mongo
  ```
- **Usuarios de prueba (Contraseña universal: `Seed1234!`):**
  - Solicitante: `lucia.gomez@comunicarlos.com`
  - Solicitante: `marcos.diaz@comunicarlos.com`
  - Operador: `rosa.molina@comunicarlos.com.ar`
  - Técnico: `ivan.rios@comunicarlos.com.ar`
  - Supervisor: `sofia.jefa@comunicarlos.com.ar`
