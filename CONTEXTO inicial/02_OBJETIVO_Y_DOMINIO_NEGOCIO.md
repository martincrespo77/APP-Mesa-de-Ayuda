# 🎯 02 — Objetivo del Proyecto y Dominio de Negocio

`[⬅️ Anterior: 01_STACK_TECNOLOGICO.md](01_STACK_TECNOLOGICO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 03_ARQUITECTURA_Y_PATRONES.md](03_ARQUITECTURA_Y_PATRONES.md)`

---

## 1. Contexto Organizacional

La **Cooperativa Comunicarlos** brinda servicios de conectividad e infraestructura (fibra óptica, telefonía IP y TV). Requiere un sistema de **Mesa de Ayuda (Help Desk)** para coordinar la resolución eficiente de incidencias técnicas y solicitudes administrativas, con trazabilidad completa de eventos y auditoría.

---

## 2. Tipos de Requerimientos

El sistema categoriza los tickets en dos jerarquías de dominio diferenciadas:

```
                  ┌──────────────────────┐
                  │    Requerimiento     │ (Clase Base / Común)
                  └──────────┬───────────┘
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
┌───────────────────────────┐     ┌───────────────────────┐
│        Incidente          │     │       Solicitud       │
├───────────────────────────┤     ├───────────────────────┤
│ - urgencia (CRITICO..MENOR)│    │ - categoria           │
│ - categoria (inaccesible, │     │   (ALTA/BAJA_SERVICIO)│
│   bloqueo SIM, pérdida)   │     │ - servicio            │
│ - servicio                │     └───────────────────────┘
│ - pasos_reproduccion      │
└───────────────────────────┘
```

* **Incidente**: Interrupción anormal o degradación de un servicio existente (ej: corte de fibra troncal). Categorías: `SERVICIO_INACCESIBLE`, `BLOQUEO_SIM`, `PERDIDA_O_DESTRUCCION_DE_EQUIPO`. Urgencia: `CRITICO`, `IMPORTANTE`, `MENOR`.
* **Solicitud de Servicio**: Pedido planificado sobre un servicio de la cooperativa. Categorías: `ALTA_SERVICIO`, `BAJA_SERVICIO`.
* Ambos tipos referencian el `servicio` de la cooperativa afectado/solicitado (ver sección 6).

---

## 3. Máquina de Estados y Ciclo de Vida

Los estados del requerimiento evolucionan de forma controlada mediante reglas de negocio:

```
[ CREADO ] ──► ABIERTO ──► EN_ANALISIS ──► EN_PROGRESO ──► RESUELTO ──► CERRADO
                 │               │               │
                 └───────────────┴───────────────┴───────────────► CANCELADO
```

* **Invariantes de transición**:
  * Un ticket en `ABIERTO` solo pasa a `EN_ANALISIS` o directamente a `CANCELADO`.
  * Pasar a `EN_PROGRESO` exige obligatoriamente un técnico asignado (`tecnico_asignado_id != None`).
  * Marcar como `RESUELTO` exige una nota de resolución técnica descriptiva.
  * Solo el solicitante, operador o supervisor pueden marcar `CERRADO` como conformidad final.
* **Reapertura**: no es un estado nuevo del diagrama. Un comentario de Operador o Técnico sobre un ticket `RESUELTO` lo devuelve a `EN_PROGRESO`, auditado como un evento `REAPERTURA` además del `COMENTARIO` (ver sección 4).
* **Derivación/interconsulta**: el Técnico actualmente asignado puede reasignar el ticket a otro Técnico mientras está `EN_ANALISIS` o `EN_PROGRESO` (evento `DERIVACION`). Mantiene el invariante de un único técnico asignado a la vez; no es una transición de estado.

---

## 4. Matriz de Roles y Permisos

El sistema cuenta con cuatro roles estrictamente diferenciados (`RolUsuario`):

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
| Administrar supervisiones (propias) | ❌ | ❌ | ❌ | ✅ |
| Recibir notificaciones de supervisados | ❌ | ❌ | ❌ | ✅ |

---

## 5. Auditoría y Trazabilidad

Cada cambio de estado, asignación o comentario genera un registro inmutable de auditoría (`EventoRequerimiento`) con:
* `id`: Identificador único.
* `requerimiento_id`: Ticket afectado.
* `tipo_evento`: (CREACION, CAMBIO_ESTADO, ASIGNACION, RESOLUCION, etc.).
* `autor_id`: Usuario que ejecutó la acción.
* `timestamp`: Fecha y hora UTC inmutable.
* `detalle`: Descripción del cambio y valores previos/nuevos.

---

## 6. Servicios de la Cooperativa y Suscripción

La cooperativa presta tres servicios (`ServicioComunicarlos`): `TELEFONIA_CELULAR`, `INTERNET_BANDA_ANCHA`, `TELEVISION`. Todo Incidente/Solicitud referencia el servicio afectado/solicitado (sección 2).

El **Solicitante** debe estar suscripto a uno o más de estos servicios (`servicios_suscriptos`, no puede ser vacío); el resto de los roles (Operador/Técnico/Supervisor) no son clientes de la cooperativa y no tienen suscripciones. Ambas reglas se validan en la propia entidad `Usuario`.

---

## 7. Notificaciones y Supervisión

Cada Supervisor audita a un conjunto de Operadores/Técnicos mediante una relación N:M (`RelacionSupervision`: `supervisor_id`/`supervisado_id`). Cuando un supervisado genera cualquier evento sobre un requerimiento (creación, cambio de estado, comentario, etc.), el sistema genera una `Notificacion` real para cada uno de sus supervisores, con el ticket, el tipo de evento y un detalle. Una notificación se puede marcar como leída, pero queda como registro permanente de auditoría (no se borra).

---

## 8. Identificación, Credenciales y Auditoría de Cuentas

El email es libre para el Solicitante y debe ser `xx@comunicarlos.com.ar` para Operador/Técnico/Supervisor (sección 4 de este documento, validado en `Usuario`). Las contraseñas se almacenan hasheadas con Bcrypt, nunca en texto plano.

Cada `Usuario` audita su propio ciclo de cuenta: `fecha_creacion` (inmutable, fijada al crear) y `ultimo_acceso` (se actualiza en cada login exitoso vía `registrar_acceso()`).

---

## 9. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Para modelar este dominio respetando los estándares de cátedra, consulta:
* [`BuenasPracticasenPython/01_principios_poo_booch.md`](BuenasPracticasenPython/01_principios_poo_booch.md): Abstracción y jerarquía polimórfica en `Incidente` y `Solicitud`.
* [`BuenasPracticasenPython/02_separacion_responsabilidades_expert.md`](BuenasPracticasenPython/02_separacion_responsabilidades_expert.md): Modelo rico vs anémico (la entidad valida sus propias transiciones de estado, incluidos comentarios y derivación).
* [`BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md`](BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md): Jerarquía de excepciones de dominio para estados inválidos y datos requeridos.
* [`BuenasPracticasenPython/07_patron_strategy.md`](BuenasPracticasenPython/07_patron_strategy.md): por qué los permisos de "Agregar comentario" (fila de la sección 4) **no** se modelan con Strategy — son 4 casos fijos por rol (Information Expert, mismo estilo que el resto de las transiciones), no algoritmos intercambiables en tiempo de ejecución.

---

`[⬅️ Anterior: 01_STACK_TECNOLOGICO.md](01_STACK_TECNOLOGICO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 03_ARQUITECTURA_Y_PATRONES.md](03_ARQUITECTURA_Y_PATRONES.md)`
