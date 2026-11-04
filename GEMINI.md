# Guía para Gemini / Antigravity — Mesa de Ayuda (Comunicarlos)

Este archivo establece las directrices de arquitectura, principios de diseño y restricciones de implementación para **Gemini / Antigravity** en este proyecto.

---

## 🏛️ Invariantes de Dominio Rico (Obligatorio)

1. **Jerarquía Polimórfica de Usuarios (`app/usuarios/dominio/`)**:
   - Cada rol de negocio es una clase concreta (`Solicitante`, `Empleado` [abstracta] -> `Operador`, `Tecnico`, `Supervisor`).
   - La clase abstracta `Usuario` responde `False` por defecto a todas las preguntas de permisos (menor privilegio).
   - `FabricaUsuarios` (Factory Method) es el **único lugar** donde un valor de `RolUsuario` se mapea a una clase.
   - Prohibido bifurcar lógica mediante `if rol == RolUsuario.X` o `if rol in [...]`.

2. **Doble Despacho (Double Dispatch)**:
   - Las operaciones de ciclo de vida en `Requerimiento` (`iniciar_analisis`, `asignar_tecnico`, `iniciar_progreso`, `resolver`, `cerrar`, `cancelar`, `agregar_comentario`, `derivar_interconsulta`) reciben la instancia completa del `actor: Usuario`.
   - `Requerimiento` consulta a `actor.puede_*(self)`.
   - El `actor` consulta al requerimiento `self.pertenece_a(actor)` o `self.esta_asignado_a(actor)`.
   - Ninguna clase viola el encapsulamiento de la otra comparando IDs o atributos internos directamente.

3. **Servicios de Aplicación Anoréxicos (Orquestación Pura)**:
   - Los servicios (`ServicioRequerimientos`, `ServicioUsuarios`, etc.) solo recuperan del repositorio (validando existencia), invocan la transición de dominio, persisten y despachan eventos a los observadores.
   - **Cero lógica de negocio en servicios**: Prohibido validar permisos o estados en los servicios.

4. **Value Objects e Inmutabilidad**:
   - Conceptos atómicos como `Email` son Value Objects inmutables con validación y normalización por construcción.
   - Las validaciones compartidas de formato (`texto_obligatorio`, `instancia_de`) residen en `app/compartido/validaciones.py`.
   - **Prohibido crear `@staticmethod` dentro de las entidades.**

5. **Seguridad en API por Capacidades**:
   - En `app/deps.py` y routers se utiliza `requerir_permiso(lambda u: u.puede_...())`, desacoplando la capa HTTP de enums o nombres de roles.

---

## ⚖️ Ciclo de Vida de Tickets
* `ABIERTO` -> `EN_ANALISIS` -> `EN_PROGRESO` -> `RESUELTO` -> `CERRADO`.
* Cancelable a `CANCELADO` desde `ABIERTO`, `EN_ANALISIS` o `EN_PROGRESO`.
* Comentario de Operador o Técnico sobre `RESUELTO` reabre a `EN_PROGRESO` (evento `REAPERTURA`).
* Derivación a otro técnico solo en `EN_ANALISIS` o `EN_PROGRESO` por el técnico asignado.

