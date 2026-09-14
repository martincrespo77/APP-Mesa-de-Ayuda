# 📋 Plan de Desarrollo por Fases: Interfaz Web para los 4 Roles
**Mesa de Ayuda — Cooperativa Comunicarlos**

Este documento define la hoja de ruta técnica y funcional para dotar al portal web (`web/`) de interfaces adaptadas a los cuatro roles del sistema: **Solicitante**, **Operador**, **Técnico** y **Supervisor**.

La construcción está dividida en **4 fases modulares e independientes** para permitir una revisión progresiva, prolija y verificable paso a paso desde el celular o navegador.

---

## 🏗️ Principios de Diseño y Arquitectura Web

1. **Tecnología limpia y sin build-step:**
   - HTML5 semántico, Vanilla CSS (diseño responsivo móvil/desktop) y Vanilla JavaScript moderno (`fetch`, `async/await`).
   - Servido directamente como archivos estáticos por FastAPI (`app.mount("/", StaticFiles(...))`).
   - Mismo origen HTTP/JSON: sin problemas de CORS.

2. **Adaptabilidad basada en Rol:**
   - Al iniciar sesión, la aplicación consulta `GET /usuarios/me` para obtener el perfil (`nombre_completo`, `email`, `rol`, `servicios_suscriptos`).
   - La navegación superior (`<nav class="pestanas">`), los filtros de tickets y los botones de acción del modal de detalle se renderizan de forma condicional según la **Matriz de Permisos** del dominio (ver `CLAUDE.md`, fuente de verdad).

3. **Invariantes del Backend:**
   - La API y las entidades de dominio (`app/requerimientos/`, `app/supervision/`, `app/notificaciones/`) ya implementan y validan todas las reglas con respuestas HTTP estándar (`200`, `201`, `400`, `403`, `404`).
   - El frontend consume los endpoints existentes **sin romper la compatibilidad** con el cliente PyQt6.
   - **Única excepción prevista:** la Fase 2 agrega un endpoint *nuevo* y acotado (`GET /usuarios/tecnicos`, ver Tarea 2.0). Es una **adición**, no una modificación de contratos existentes: ningún endpoint, schema ni permiso vigente cambia, por lo que `desktop/` sigue funcionando sin tocar una línea.
   - La UI no inventa reglas de negocio: solo **oculta** lo que el dominio ya rechazaría. Cualquier botón que se muestre debe corresponder a una transición válida y autorizada.

---

## 📌 Fase 1: Rol Solicitante (Cliente / Abonado)
*Perfil de prueba:* `lucia.gomez@comunicarlos.com` o `marcos.diaz@comunicarlos.com` (Pass: `Seed1234!`)

### Objetivo
Optimizar el portal de autoservicio para el cliente final, garantizando que cree y gestione tickets prolijamente sobre sus servicios contratados y consulte solo sus propios requerimientos.

### Alcance Funcional
1. **Pestaña "Nuevo Requerimiento":**
   - Selector reactivo: **Incidente** (con urgencia, categoría y pasos de reproducción) vs **Solicitud** (alta/baja de servicio).
   - El selector de "Servicio" se filtra dinámicamente según los `servicios_suscriptos` del usuario (`TELEFONIA_CELULAR`, `INTERNET_BANDA_ANCHA`, `TELEVISION`).
     - **Motivo:** es una mejora de **UX y consistencia de datos** — le evita al abonado elegir un servicio que no tiene contratado y previene tickets ilógicos (reclamos de TV de alguien que solo tiene internet).
     - **Aclaración técnica importante:** hoy el backend **no** valida el cruce entre `Usuario.servicios_suscriptos` y el campo `servicio` del Incidente/Solicitud (verificado en `app/requerimientos/dominio/incidente.py`, `solicitud.py` y `app/requerimientos/servicios.py`). Es decir, este filtro **no** está esquivando un `400` del dominio, porque ese `400` no existe: es una restricción puramente de interfaz.
     - **Nota de alcance:** si en el futuro se quisiera reforzar la regla en el dominio (que un Solicitante no pueda crear un requerimiento sobre un servicio al que no está suscripto), sería una **tarea de backend aparte**, fuera del alcance de esta fase de frontend.
2. **Pestaña "Mis Requerimientos":**
   - Listado exclusivo de sus tickets (la API ya filtra por `solicitante_id`).
   - Badges visuales con código de colores según el estado (`ABIERTO`, `EN_ANALISIS`, `EN_PROGRESO`, `RESUELTO`, `CERRADO`, `CANCELADO`).
   - Filtro rápido por estado (Todos / Activos / Finalizados).
3. **Detalle del Ticket:**
   - Visualización de datos completos e historial cronológico de auditoría (`EventoRequerimiento`).
   - **Acciones permitidas al Solicitante:**
     - **"Cancelar ticket"**: visible únicamente si el estado es `ABIERTO` (`POST /requerimientos/{id}/cancelar`).
     - **"Confirmar cierre"**: visible únicamente si el estado es `RESUELTO` (`POST /requerimientos/{id}/cerrar`).
     - **"Agregar comentario"**: campo de texto para agregar seguimiento a su ticket (`POST /requerimientos/{id}/comentarios`).
4. **Restricciones:** Ocultar cualquier botón técnico (asignar, derivar, resolver, iniciar progreso).

### Criterio de Aceptación y Verificación
- Iniciar sesión como `lucia.gomez@comunicarlos.com`.
- Crear un incidente sobre Internet.
- Comentar en el ticket.
- Verificar que el selector de servicios solo ofrezca los servicios suscriptos del usuario.
- Verificar que no aparezca ningún botón de operador/técnico.

---

## 📌 Fase 2: Rol Operador (Mesa de Entrada / Triage)
*Perfil de prueba:* `rosa.molina@comunicarlos.com.ar` (Pass: `Seed1234!`)

### Objetivo
Permitir a los operadores recibir todos los tickets entrantes de la cooperativa, evaluar su criticidad, iniciar el análisis y asignarlos a los técnicos correspondientes.

### 🔧 Tarea 2.0 (Backend — bloqueante, se hace primero)
**Nuevo endpoint acotado para listar técnicos: `GET /usuarios/tecnicos`.**

- **Problema a resolver:** hoy el único listado de usuarios es `GET /usuarios` (`app/usuarios/router.py:78-86`), gateado con `requerir_rol(RolUsuario.SUPERVISOR)`. Por lo tanto, un **Operador no tiene ninguna forma de obtener la lista de técnicos** para poblar el dropdown de "Asignar Técnico" (Fase 2), ni un **Técnico** para el dropdown de "Derivar a otro técnico" (Fase 3). Sin este endpoint, ambas pantallas quedarían obligadas a pedir el UUID tipeado a mano.
- **Contrato esperado:**
  - Devuelve **solo** usuarios con rol `TECNICO`.
  - Payload **mínimo**: `id` + `nombre_completo`. No exponer email, hash, `servicios_suscriptos`, fechas ni ningún otro campo sensible: es un dropdown, no una vista de administración. Conviene un schema de respuesta propio y reducido en `app/usuarios/schemas.py` en lugar de reutilizar `UsuarioResponse`.
  - Accesible para `OPERADOR`, `TECNICO` y `SUPERVISOR`. **No** para `SOLICITANTE`. `requerir_rol(*roles)` ya acepta varios roles, así que alcanza con enumerarlos en la dependencia.
  - Considerar devolver únicamente técnicos **activos** (`activo == True`), para no ofrecer en el dropdown a alguien dado de baja.
- **Ubicación y estilo (DDD-lite):**
  - El endpoint va en `app/usuarios/router.py`. **La lógica no vive en el router:** si hace falta, se agrega un método al servicio de usuarios (`app/usuarios/servicios.py`, en la línea de `listar_todos`) y, si corresponde, su contraparte en `app/usuarios/repositorio.py`, para que el router solo orqueste y serialice.
  - Atención al **orden de declaración de rutas** en FastAPI: una ruta literal como `/tecnicos` debe declararse antes de cualquier ruta paramétrica `GET /{usuario_id}` que se agregue en el futuro.
- **Encuadre:** es una **ampliación acotada y aditiva** del backend. No modifica ningún endpoint, schema ni permiso existente, por lo que respeta el invariante "el frontend consume endpoints existentes sin romper compatibilidad" — nada de lo que consume `desktop/` se ve afectado.
- **Verificación:** probar con token de Operador (200), de Técnico (200), de Supervisor (200) y de Solicitante (403). Agregar el request a la colección de `bruno/` siguiendo el patrón ya documentado en `bruno/README.md`.

### Alcance Funcional
1. **Bandeja General de Requerimientos:**
   - Visualización de **todos** los requerimientos de la cooperativa (la API para rol `OPERADOR` devuelve la totalidad de los tickets).
   - Filtros avanzados:
     - Por Estado (`ABIERTO`, `EN_ANALISIS`, etc.).
     - Por Urgencia (`CRITICO`, `IMPORTANTE`, `MENOR`).
     - Por Servicio.
   - Resaltado visual de advertencia para incidentes `CRITICO` en estado `ABIERTO` o sin técnico asignado.
2. **Detalle del Ticket y Acciones del Operador:**
   - **"Iniciar análisis"** (`POST /requerimientos/{id}/iniciar-analisis`):
     - Visible cuando el ticket está en `ABIERTO`.
     - Pasa el estado a `EN_ANALISIS`.
   - **"Asignar Técnico"** (`POST /requerimientos/{id}/asignar-tecnico`):
     - Visible cuando el ticket está en `EN_ANALISIS` y no tiene técnico asignado.
     - Selector desplegable amigable poblado con `GET /usuarios/tecnicos` (ej. Iván Ríos), en lugar de requerir tipeo manual de UUID.
   - **"Cancelar / Desestimar"** (`POST /requerimientos/{id}/cancelar`):
     - Permite cancelar solicitudes o incidentes duplicados o erróneos.
   - **"Agregar comentario de seguimiento"** (`POST /requerimientos/{id}/comentarios`):
     - Permite al operador dejar notas.
     - Si el ticket estaba `RESUELTO`, el comentario ejecuta la regla de negocio de **reapertura automática** devolviéndolo a `EN_PROGRESO` (evento `REAPERTURA`).

### Criterio de Aceptación y Verificación
- Verificar primero la Tarea 2.0: `GET /usuarios/tecnicos` responde con los técnicos para Operador/Técnico/Supervisor y `403` para Solicitante.
- Iniciar sesión como `rosa.molina@comunicarlos.com.ar`.
- Ver tickets de todos los clientes.
- Tomar un ticket `ABIERTO` -> Iniciar análisis -> Asignar a `Iván Ríos` **eligiéndolo del dropdown** (sin escribir UUID).
- Verificar en el historial el evento `ASIGNACION`.

---

## 📌 Fase 3: Rol Técnico (Resolución y Soporte de Campo)
*Perfil de prueba:* `ivan.rios@comunicarlos.com.ar` (Pass: `Seed1234!`)

### Objetivo
Permitir a los técnicos gestionar sus órdenes de trabajo asignadas, iniciar el trabajo técnico, transferir/derivar tickets por interconsulta y registrar la resolución técnica.

### Alcance Funcional
1. **Pestaña "Mis Asignaciones" (Vista Predeterminada):**
   - Listado enfocado exclusivamente en los requerimientos asignados al técnico autenticado (`tecnico_asignado_id == usuario.id`).
   - Pestaña o toggle secundario "Todos los tickets" (modo consulta de contexto).
2. **Detalle del Ticket y Acciones del Técnico:**
   - **"Iniciar progreso"** (`POST /requerimientos/{id}/iniciar-progreso`):
     - Visible cuando el ticket está `EN_ANALISIS` y tiene técnico asignado.
     - Habilitado para el **Técnico asignado** o para un **Supervisor** (el dominio lo valida en `app/requerimientos/dominio/base.py`, método `_exigir_rol_o_asignado`; coincide con la matriz de `CLAUDE.md`: "Iniciar progreso del ticket — Técnico ✅ si asignado | Supervisor ✅").
     - Pasa el estado a `EN_PROGRESO`.
   - **"Derivar a otro técnico" (Interconsulta)** (`POST /requerimientos/{id}/derivar`):
     - Visible mientras el ticket está `EN_ANALISIS` o `EN_PROGRESO`, y **solo para el técnico actualmente asignado**.
     - Modal con selector de técnico destino poblado con `GET /usuarios/tecnicos` (Tarea 2.0). Reasigna el ticket manteniendo la trazabilidad con evento `DERIVACION`.
   - **"Resolver ticket"** (`POST /requerimientos/{id}/resolver`):
     - Visible cuando el ticket está `EN_PROGRESO` (Técnico asignado o Supervisor).
     - Formulario modal con campo obligatorio: **Nota de resolución técnica** (explicación de la solución aplicada).
     - Pasa el estado a `RESUELTO`.
   - **"Agregar comentario técnico"** (`POST /requerimientos/{id}/comentarios`):
     - Permite dejar comentarios sobre el diagnóstico técnico.

### Criterio de Aceptación y Verificación
- Iniciar sesión como `ivan.rios@comunicarlos.com.ar`.
- Acceder al ticket asignado en la Fase 2.
- Iniciar progreso (`EN_PROGRESO`).
- Derivar un ticket a otro técnico desde el dropdown y verificar el evento `DERIVACION`.
- Resolver el ticket cargando la nota de resolución.
- Verificar que el ticket pase a `RESUELTO`.

---

## 📌 Fase 4: Rol Supervisor (Auditoría, Control y Notificaciones)
*Perfil de prueba:* `sofia.jefa@comunicarlos.com.ar` (Pass: `Seed1234!`)

### Objetivo
Brindar al supervisor control integral sobre las operaciones de la cooperativa: recepción en tiempo real de notificaciones de sus supervisados, administración del equipo y una vista global de métricas.

### Alcance Funcional
1. **Pestaña "Notificaciones" (Nueva para Supervisor):**
   - Indicador / campana con contador de notificaciones no leídas (`GET /notificaciones`).
   - Lista cronológica de notificaciones generadas por el patrón Observer (acciones de sus operadores/técnicos supervisados).
   - Botón individual "Marcar como leída" (`PATCH /notificaciones/{id}/leida`).
   - Enlace directo desde la notificación para abrir el detalle del ticket correspondiente.
2. **Pestaña "Equipo Supervisado" (Nueva para Supervisor):**
   - Lista de operadores y técnicos actualmente asignados a su supervisión (`GET /supervisiones`).
   - Opción para agregar nuevo supervisado (`POST /supervisiones`) o removerlo (`DELETE /supervisiones/{supervisado_id}`).
3. **Panel Global (vista completa + métricas):**
   - Vista completa de todos los tickets con métricas básicas: **total abiertos**, **críticos**, **resueltos** (calculadas en el frontend a partir del listado que ya devuelve la API para rol `SUPERVISOR`).
   - Acciones habilitadas: las que el Supervisor **ya tiene** por la matriz de roles, ejerciéndolas sobre cualquier ticket sin necesidad de ser el técnico asignado:
     - Iniciar análisis / Asignar técnico.
     - Iniciar progreso / Resolver (con nota).
     - Dar cierre de conformidad.
     - Cancelar / Desestimar.
   - **Restricción de alcance (explícita):** estas acciones se ejercen **siempre dentro de las transiciones de estado normales validadas por el dominio**. La UI del Supervisor **no** ofrece saltear precondiciones ni atajos de estado: nada de resolver un ticket `ABIERTO`, nada de cerrar sin pasar por `RESUELTO`. El privilegio del Supervisor es de **rol** (no necesita ser el asignado), no de **ciclo de vida**.

### Criterio de Aceptación y Verificación
- Iniciar sesión como `sofia.jefa@comunicarlos.com.ar`.
- Abrir la pestaña de notificaciones y comprobar que figure la notificación del ticket resuelto en la Fase 3.
- Marcar la notificación como leída y ver que se actualice el contador.
- Probar agregar y remover una relación de supervisión.
- Verificar que el Panel Global muestre los contadores de abiertos / críticos / resueltos coherentes con el listado.
- Verificar que en un ticket `ABIERTO` el Supervisor solo vea acciones válidas para ese estado (iniciar análisis / cancelar), y ninguna acción de resolución o cierre.

---

## 🔄 Resumen de Estados y Transiciones en UI

| Estado Actual | Acciones Posibles según Rol | Siguiente Estado |
| :--- | :--- | :--- |
| `ABIERTO` | Operador / Supervisor: Iniciar análisis<br>Solicitante / Operador / Supervisor: Cancelar | `EN_ANALISIS`<br>`CANCELADO` |
| `EN_ANALISIS` | Operador / Supervisor: Asignar técnico<br>Técnico asignado / Supervisor: Iniciar progreso<br>Técnico asignado: Derivar a otro técnico | (Asignado)<br>`EN_PROGRESO`<br>(Nuevo técnico) |
| `EN_PROGRESO` | Técnico asignado / Supervisor: Resolver (con nota)<br>Técnico asignado: Derivar a otro técnico | `RESUELTO`<br>(Nuevo técnico) |
| `RESUELTO` | Solicitante / Operador / Supervisor: Confirmar cierre<br>Operador / Técnico: Comentar (Reapertura) | `CERRADO`<br>`EN_PROGRESO` |
| `CERRADO` | Ninguna (Estado final) | — |
| `CANCELADO` | Ninguna (Estado final) | — |

> [!NOTE]
> `EN_ANALISIS -> EN_PROGRESO` requiere que el ticket **tenga técnico asignado** (regla 2 del ciclo de vida en `CLAUDE.md`), independientemente de quién dispare la acción.
