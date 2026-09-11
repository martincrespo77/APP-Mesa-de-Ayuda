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
┌───────────────────────┐         ┌───────────────────────┐
│       Incidente       │         │       Solicitud       │
├───────────────────────┤         ├───────────────────────┤
│ - severidad (BAJA..CR)│         │ - categoria           │
│ - pasos_reproduccion  │         │ - fecha_limite        │
│ - servicio_afectado   │         │ - impacto_estimado    │
└───────────────────────┘         └───────────────────────┘
```

* **Incidente**: Interrupción anormal o degradación de un servicio existente (ej: corte de fibra troncal, caída de DNS). Requiere severidad e impacto técnico.
* **Solicitud de Servicio**: Pedido planificado de nuevo servicio, cambio de abono o consulta administrativa/facturación.

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
| Administrar usuarios | ❌ | ❌ | ❌ | ✅ |

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

## 6. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Para modelar este dominio respetando los estándares de cátedra, consulta:
* [`BuenasPracticasenPython/01_principios_poo_booch.md`](BuenasPracticasenPython/01_principios_poo_booch.md): Abstracción y jerarquía polimórfica en `Incidente` y `Solicitud`.
* [`BuenasPracticasenPython/02_separacion_responsabilidades_expert.md`](BuenasPracticasenPython/02_separacion_responsabilidades_expert.md): Modelo rico vs anémico (la entidad valida sus propias transiciones de estado).
* [`BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md`](BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md): Jerarquía de excepciones de dominio para estados inválidos y datos requeridos.

---

`[⬅️ Anterior: 01_STACK_TECNOLOGICO.md](01_STACK_TECNOLOGICO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 03_ARQUITECTURA_Y_PATRONES.md](03_ARQUITECTURA_Y_PATRONES.md)`
