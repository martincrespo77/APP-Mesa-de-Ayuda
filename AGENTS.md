# Standard Agent Instructions (AGENTS.md)

Este repositorio aplica una arquitectura de **Modelo de Dominio Rico (Rich Domain Model)** con **Domain-Driven Design (DDD)** estricto. Cualquier agente de codificación (Claude, Gemini, Cursor, Codex, etc.) debe acatar las siguientes invariantes inmutables.

---

## 🏛️ Invariantes de Dominio y Orientación a Objetos

1. **Polimorfismo por Rol:**
   - La entidad `Usuario` es una clase abstracta. Cada rol es una clase concreta (`Solicitante`, `Operador`, `Tecnico`, `Supervisor`), agrupadas las tres últimas bajo la clase abstracta intermedia `Empleado`.
   - Prohibido el uso de condicionales sobre `rol` (`if rol == ...`).
   - La creación polimórfica está centralizada en `FabricaUsuarios` (Factory Method).

2. **Principio Tell, Don't Ask & Doble Despacho (Double Dispatch):**
   - Las transiciones de estado de `Requerimiento` reciben la entidad `actor: Usuario` completa.
   - `Requerimiento` pregunta al actor: `actor.puede_*(self)`.
   - El actor le pregunta al ticket: `self.pertenece_a(actor)` o `self.esta_asignado_a(actor)`.
   - Ninguna clase inspecciona ni compara atributos internos de la otra.

3. **Servicios de Aplicación como Orquestadores Puros (Thin Services):**
   - Los servicios en `app/*/servicios.py` no contienen lógica de negocio ni sentencias `if` sobre roles o estados.
   - Su responsabilidad se limita a: recuperar del repositorio, invocar la transición de dominio, guardar en repositorio y notificar eventos mediante `DespachadorEventos` (Observer).

4. **Value Objects y Prohibición de `@staticmethod`:**
   - Conceptos con formato o reglas canónicas (`Email`, `Comentario`, etc.) se modelan como Value Objects inmutables.
   - Las funciones de validación de formato compartidas residen en `app/compartido/validaciones.py`.
   - Queda terminantemente prohibido definir `@staticmethod` dentro de las entidades de dominio.

5. **Seguridad y Presentación Desacoplada:**
   - Las dependencias FastAPI utilizan `requerir_permiso(lambda u: u.puede_...())`, verificando capacidades polimórficas del usuario autenticado en lugar de strings o enums de roles.

