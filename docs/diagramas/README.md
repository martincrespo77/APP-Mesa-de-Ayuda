# 📊 Diagramas Técnicos e Interactivos — Mesa de Ayuda (PP5)

Este directorio contiene los diagramas arquitectónicos y de modelado de software para el sistema **Mesa de Ayuda — Cooperativa Comunicarlos**, compilados en aplicaciones web interactivas (Single-File Bundle: HTML5 + SVG + Vanilla JS, 100% Air-Gapped) utilizando el servidor MCP `mcp-diagrama-iterativo-mermaid`.

---

## 🌟 Suite Unificada Multi-pestaña (Recomendada)

La suite unificada integra en **un solo visor con pestañas superiores** toda la arquitectura del sistema:

👉 **[Abrir Suite Unificada Interactiva (`diagrama_suite_unificada.html`)](diagrama_suite_unificada.html)**

### Pestañas Disponibles en la Suite:
1. 🎯 **Casos de Uso:** Mapa de los 4 actores (`Solicitante`, `Operador`, `Técnico`, `Supervisor`) y los casos de uso delimitados por módulos funcionales con relaciones `<<include>>` y `<<extend>>`.
2. 🔀 **Flujos de Procesos:**
   - *Ciclo de Vida del Requerimiento:* Simulador de escenarios (Camino feliz completo, Rechazo por falta de suscripción, Cancelación en triage, Derivación/interconsulta y Reapertura automática).
   - *Flujo de Notificaciones y Supervisión:* Despacho Observer y persistencia en MongoDB para supervisores a cargo.
3. ⏱️ **Secuencia UML:** Secuencia multicapa interactiva con botones paso a paso, llamadas, respuestas y notas técnicas (*Creación de Requerimiento* y *Resolución Técnica con Alerta a Supervisor*).
4. 🏛️ **Clases del Dominio:** Entidades DDD (`Requerimiento`, `Incidente`, `Solicitud`), jerarquía polimórfica de `Usuario` por rol (`Solicitante`, `Empleado` → `Operador` / `Tecnico` / `Supervisor`), Value Object `Email`, fábricas polimórficas (`FabricaRequerimientos`, `FabricaUsuarios`), Servicios de Aplicación, Puertos y Adaptadores PyMongo con filtros por capas y modo enfoque (tracing de dependencias).

---

## 📂 Catálogo de Diagramas Individuales

Para visualización focalizada o consulta de fuentes Mermaid versionables:

| # | Tipo de Diagrama | Código Fuente Mermaid (.mmd) | Visor Interactivo Autónomo (.html) | Descripción y Alcance |
|:---:|:---|:---|:---|:---|
| **1** | **Diagrama de Clases** | [`diagrama_clases.mmd`](diagrama_clases.mmd) | [`diagrama_clases.html`](diagrama_clases.html) | Modelo de dominio rico: jerarquías polimórficas de `Requerimiento` (`Incidente`, `Solicitud`) y de `Usuario` por rol (`Solicitante`, `Empleado` → `Operador` / `Tecnico` / `Supervisor`), double dispatch entre ambas (`actor.puede_*(req)` / `req.pertenece_a(actor)`), fábricas (`Factory Method`), Value Object `Email`, `RelacionSupervision` con comportamiento (`notificar`), servicios de aplicación que solo orquestan, `requerir_permiso`, puertos (`Dependency Inversion`), adaptadores PyMongo y patrón Observer. |
| **2** | **Diagrama de Flujo** | [`diagrama_flujo.mmd`](diagrama_flujo.mmd) | [`diagrama_flujo.html`](diagrama_flujo.html) | Flujo de procesos y ciclo de vida de punta a punta entre los 4 roles: apertura y validación de contrato, triage, asignación, inicio de progreso, derivación/interconsulta, resolución con nota descriptiva, reapertura automática y alertas a supervisores. |
| **3** | **Diagrama de Casos de Uso** | [`diagrama_casos_de_uso.mmd`](diagrama_casos_de_uso.mmd) | [`diagrama_casos_de_uso.html`](diagrama_casos_de_uso.html) | Modelado UML de los 4 actores del sistema contra los 28 casos de uso delimitados por subsistemas, con relaciones `<<include>>` (validación de suscripción, exigencia de nota técnica, alertas) y `<<extend>>` (reapertura automática a `EN_PROGRESO` tras comentario en ticket `RESUELTO`). |
| **4** | **Diagrama de Secuencia** | [`diagrama_secuencia.mmd`](diagrama_secuencia.mmd)<br/>[`diagrama_secuencia_estandar.mmd`](diagrama_secuencia_estandar.mmd) | [`diagrama_secuencia.html`](diagrama_secuencia.html) | Interacción secuencial paso a paso a través de las capas arquitectónicas (Cliente Web/Desktop → Router FastAPI → `obtener_usuario_actual` / `requerir_permiso` → Servicio de Aplicación → Dominio DDD con double dispatch actor/ticket → Persistencia PyMongo → Bus de Eventos Observer → `RelacionSupervision.notificar`). Incluye variante interactiva y variante estándar lifeline para GitHub. |

---

## 🔄 Cómo Regenerar los Visores tras Editar un `.mmd`

Los `.mmd` son la fuente de verdad. Los visores `diagrama_clases.html` y `diagrama_secuencia.html` embeben esa fuente compilada en tres constantes JSON (`nodesData`, `connectionsData`, `subgraphsData`); el script [`compilar_mermaid.py`](compilar_mermaid.py) las regenera sin tocar el resto de la plantilla:

```bash
python docs/diagramas/compilar_mermaid.py docs/diagramas/diagrama_clases.mmd docs/diagramas/diagrama_secuencia.mmd
```

La suite unificada (`diagrama_suite_unificada.html`) no se compila desde Mermaid: sus datos (`CLASSES`, `CEDGES`, `SEQS`) se editan directamente en el archivo y el layout lo calcula el propio visor.

---

## 🚀 Cómo Abrir y Utilizar los Diagramas

Cada archivo `.html` es un artefacto **100% independiente y autónomo (Air-Gapped)** que no requiere internet, node, servidores web ni dependencias externas.

### Características de la Interfaz:
- **Arrastrar y Soltar (Drag & Drop):** Posiciona libremente cualquier nodo para acomodar la vista con conectores SVG dinámicos calculados trigonométricamente (`atan2`).
- **Simulador de Caminos y Escenarios:** En la pestaña *Flujos*, selecciona cualquier escenario (ej: *Reapertura automática* o *Derivación técnica*) para resaltar el camino en color y ver los Casos de Prueba asociados.
- **Modo Enfoque (Tracing):** Haz doble clic en cualquier nodo para aislar sus relaciones entrantes y salientes.
- **Buscador en Vivo (Ctrl+K):** Filtra rápidamente clases, métodos, rutas y decisiones.
- **Minimapa Reactivo:** Navegación en miniatura en la esquina inferior.
- **Tema Claro / Oscuro:** Alterna con el botón superior.

### Comandos para Visualizar en Linux:
```bash
# Abrir la Suite Unificada (Recomendado):
xdg-open docs/diagramas/diagrama_suite_unificada.html

# O abrir los diagramas individuales:
xdg-open docs/diagramas/diagrama_clases.html
xdg-open docs/diagramas/diagrama_flujo.html
xdg-open docs/diagramas/diagrama_casos_de_uso.html
xdg-open docs/diagramas/diagrama_secuencia.html
```
