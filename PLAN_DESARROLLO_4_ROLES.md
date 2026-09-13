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
   - La navegación superior (`<nav class="pestanas">`), los filtros de tickets y los botones de acción del modal de detalle se renderizan de forma condicional según la **Matriz de Permisos** del dominio.

3. **Invariantes del Backend:**
   - La API y las entidades de dominio (`app/requerimientos/`, `app/supervision/`, `app/notificaciones/`) ya implementan y validan todas las reglas con respuestas HTTP estándar (`200`, `201`, `400`, `403`, `404`).
   - El frontend consume los endpoints existentes sin romper la compatibilidad con el cliente PyQt6.

---

## 📌 Fase 1: Rol Solicitante (Cliente / Abonado)
*Perfil de prueba:* `lucia.gomez@comunicarlos.com` o `marcos.diaz@comunicarlos.com` (Pass: `Seed1234!`)

### Objetivo
Optimizar el portal de autoservicio para el cliente final, garantizando que solo cree y gestione tickets sobre sus servicios contratados y consulte sus propios requerimientos.

### Alcance Funcional
1. **Pestaña "Nuevo Requerimiento":**
   - Selector reactivo: **Incidente** (con urgencia, categoría y pasos de reproducción) vs **Solicitud** (alta/baja de servicio).
   - El selector de "Servicio" se filtra dinámicamente según los `servicios_suscriptos` del usuario (`TELEFONIA_CELULAR`, `INTERNET_BANDA_ANCHA`, `TELEVISION`). Si no está suscripto a un servicio, no se le permite seleccionarlo (evita el error 400 del dominio).
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
- Verificar que no aparezca ningún botón de operador/técnico.

---

## 📌 Fase 2: Rol Operador (Mesa de Entrada / Triage)
*Perfil de prueba:* `rosa.molina@comunicarlos.com.ar` (Pass: `Seed1234!`)

### Objetivo
Permitir a los operadores recibir todos los tickets entrantes de la cooperativa, evaluar su criticidad, iniciar el análisis y asignarlos a los técnicos correspondientes.

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
     - Selector desplegable amigable con los técnicos disponibles (ej. Iván Ríos) en lugar de requerir tipeo manual de UUID.
   - **"Cancelar / Desestimar"** (`POST /requerimientos/{id}/cancelar`):
     - Permite cancelar solicitudes o incidentes duplicados o erróneos.
   - **"Agregar comentario de seguimiento"** (`POST /requerimientos/{id}/comentarios`):
     - Permite al operador dejar notas.
     - Si el ticket estaba `RESUELTO`, el comentario ejecuta la regla de negocio de **reapertura automática** devolviéndolo a `EN_PROGRESO` (evento `REAPERTURA`).

### Criterio de Aceptación y Verificación
- Iniciar sesión como `rosa.molina@comunicarlos.com.ar`.
- Ver tickets de todos los clientes.
- Tomar un ticket `ABIERTO` -> Iniciar análisis -> Asignar a `Iván Ríos`.
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
     - Visible cuando el ticket está `EN_ANALISIS` y asignado a este técnico.
     - Pasa el estado a `EN_PROGRESO`.
   - **"Derivar a otro técnico" (Interconsulta)** (`POST /requerimientos/{id}/derivar`):
     - Visible mientras el ticket está `EN_ANALISIS` o `EN_PROGRESO`.
     - Modal con selector de técnico destino. Reasigna el ticket manteniendo la trazabilidad con evento `DERIVACION`.
   - **"Resolver ticket"** (`POST /requerimientos/{id}/resolver`):
     - Visible cuando el ticket está `EN_PROGRESO`.
     - Formulario modal con campo obligatorio: **Nota de resolución técnica** (explicación de la solución aplicada).
     - Pasa el estado a `RESUELTO`.
   - **"Agregar comentario técnico"** (`POST /requerimientos/{id}/comentarios`):
     - Permite dejar comentarios sobre el diagnóstico técnico.

### Criterio de Aceptación y Verificación
- Iniciar sesión como `ivan.rios@comunicarlos.com.ar`.
- Acceder al ticket asignado en la Fase 2.
- Iniciar progreso (`EN_PROGRESO`).
- Resolver el ticket cargando la nota de resolución.
- Verificar que el ticket pase a `RESUELTO`.

---

## 📌 Fase 4: Rol Supervisor (Auditoría, Control y Notificaciones)
*Perfil de prueba:* `sofia.jefa@comunicarlos.com.ar` (Pass: `Seed1234!`)

### Objetivo
Brindar al supervisor control integral sobre las operaciones de la cooperativa: recepción en tiempo real de notificaciones de sus supervisados, administración del equipo y acciones de contingencia.

### Alcance Funcional
1. **Pestaña "Notificaciones" (Nueva para Supervisor):**
   - Indicador / campana con contador de notificaciones no leídas (`GET /notificaciones`).
   - Lista cronológica de notificaciones generadas por el patrón Observer (acciones de sus operadores/técnicos supervisados).
   - Botón individual "Marcar como leída" (`PATCH /notificaciones/{id}/leida`).
   - Enlace directo desde la notificación para abrir el detalle del ticket correspondiente.
2. **Pestaña "Equipo Supervisado" (Nueva para Supervisor):**
   - Lista de operadores y técnicos actualmente asignados a su supervisión (`GET /supervisiones`).
   - Opción para agregar nuevo supervisado (`POST /supervisiones`) o removerlo (`DELETE /supervisiones/{supervisado_id}`).
3. **Panel Global y Acciones de Contingencia:**
   - Vista completa de todos los tickets con métricas básicas (Total abiertos, críticos, resueltos).
   - Acciones de contingencia autorizadas por la matriz de roles para el Supervisor:
     - Forzar asignación de técnico.
     - Forzar resolución o cierre de tickets trabados.

### Criterio de Aceptación y Verificación
- Iniciar sesión como `sofia.jefa@comunicarlos.com.ar`.
- Abrir la pestaña de notificaciones y comprobar que figure la notificación del ticket resuelto en la Fase 3.
- Marcar la notificación como leída y ver que se actualice el contador.
- Probar agregar y remover una relación de supervisión.

---

## 🔄 Resumen de Estados y Transiciones en UI

| Estado Actual | Acciones Posibles según Rol | Siguiente Estado |
| :--- | :--- | :--- |
| `ABIERTO` | Operador / Supervisor: Iniciar análisis<br>Solicitante / Operador / Supervisor: Cancelar | `EN_ANALISIS`<br>`CANCELADO` |
| `EN_ANALISIS` | Operador / Supervisor: Asignar técnico<br>Técnico asignado: Iniciar progreso<br>Técnico asignado: Derivar a otro técnico | (Asignado)<br>`EN_PROGRESO`<br>(Nuevo técnico) |
| `EN_PROGRESO` | Técnico asignado / Supervisor: Resolver (con nota)<br>Técnico asignado: Derivar a otro técnico | `RESUELTO`<br>(Nuevo técnico) |
| `RESUELTO` | Solicitante / Operador / Supervisor: Confirmar cierre<br>Operador / Técnico: Comentar (Reapertura) | `CERRADO`<br>`EN_PROGRESO` |
| `CERRADO` | Ninguna (Estado final) | — |
| `CANCELADO` | Ninguna (Estado final) | — |
