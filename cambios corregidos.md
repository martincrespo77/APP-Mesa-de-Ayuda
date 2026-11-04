# Análisis Integral del Refactor: Modelo de Dominio Rico y Polimorfismo

> **Guía Pedagógica y Técnica para NotebookLM**  
> **Proyecto:** Sistema de Mesa de Ayuda — Cooperativa *Comunicarlos*  
> **Objetivo:** Explicar detalladamente la transformación arquitectónica desde un modelo de dominio anémico (basado en datos y condicionales `if`) hacia un modelo de dominio rico orientado a objetos con jerarquía polimórfica, doble despacho (*double dispatch*) y orquestación desacoplada.  
> **Estructura:** 20 partes temáticas independientes, ideales para generación de podcasts, resúmenes conceptuales y guiones de video.

---

## Índice General

1. [Parte 1: El Diagnóstico Inicial y la Observación de Cátedra](#parte-1-el-diagnóstico-inicial-y-la-observación-de-cátedra)
2. [Parte 2: La Arquitectura General del Refactor (Opción B: Dominio Rico)](#parte-2-la-arquitectura-general-del-refactor-opción-b-dominio-rico)
3. [Parte 3: La Jerarquía de Usuarios — Clase Abstracta Raíz `Usuario`](#parte-3-la-jerarquía-de-usuarios--clase-abstracta-raíz-usuario)
4. [Parte 4: La Invariante Corporativa — Clase Abstracta `Empleado`](#parte-4-la-invariante-corporativa--clase-abstracta-empleado)
5. [Parte 5: Rol `Solicitante` — El Cliente y el Principio de Pertenencia](#parte-5-rol-solicitante--el-cliente-y-el-principio-de-pertenencia)
6. [Parte 6: Rol `Operador` — Mesa de Entrada, Triage y Seguimiento](#parte-6-rol-operador--mesa-de-entrada-triage-y-seguimiento)
7. [Parte 7: Rol `Tecnico` — Responsabilidad de Resolución y Asignación Exclusiva](#parte-7-rol-tecnico--responsabilidad-de-resolución-y-asignación-exclusiva)
8. [Parte 8: Rol `Supervisor` — Autoridad Operativa y Capacidad de Supervisión](#parte-8-rol-supervisor--autoridad-operativa-y-capacidad-de-supervisión)
9. [Parte 9: El Patrón Factory Method — `FabricaUsuarios`](#parte-9-el-patrón-factory-method--fabricausuarios)
10. [Parte 10: Value Object `Email` — Canonicidad e Inmutabilidad sin Excepciones](#parte-10-value-object-email--canonicidad-e-inmutabilidad-sin-excepciones)
11. [Parte 11: Shared Kernel — `validaciones.py` y la Extinción de `@staticmethod`](#parte-11-shared-kernel--validacionespy-y-la-extinción-de-staticmethod)
12. [Parte 12: Doble Despacho (*Double Dispatch*) entre `Requerimiento` y `Usuario`](#parte-12-doble-despacho-double-dispatch-entre-requerimiento-y-usuario)
13. [Parte 13: Transiciones de Estado en `Requerimiento` — Desaparición de `(autor_id, rol_actor)`](#parte-13-transiciones-de-estado-en-requerimiento--desaparición-de-autor_id-rol_actor)
14. [Parte 14: Validación de Destinatarios de Asignación e Interconsulta en el Dominio](#parte-14-validación-de-destinatarios-de-asignación-e-interconsulta-en-el-dominio)
15. [Parte 15: Servicios de Aplicación Anoréxicos — Orquestación Pura y `_aplicar_transicion`](#parte-15-servicios-de-aplicación-anoréxicos--orquestación-pura-y-_aplicar_transicion)
16. [Parte 16: Dominio de Supervisión y Notificaciones con Comportamiento Activo](#parte-16-dominio-de-supervisión-y-notificaciones-con-comportamiento-activo)
17. [Parte 17: Seguridad y Presentación en FastAPI — De `requerir_rol` a `requerir_permiso`](#parte-17-seguridad-y-presentación-en-fastapi--de-requerir_rol-a-requerir_permiso)
18. [Parte 18: Hallazgos Críticos Corregidos en la Revisión `xhigh`](#parte-18-hallazgos-críticos-corregidos-en-la-revisión-xhigh)
19. [Parte 19: La Suite de Pruebas Automatizadas — De 257 a 372 Tests](#parte-19-la-suite-de-pruebas-automatizadas--de-257-a-372-tests)
20. [Parte 20: Documentación Viva y Compilación de Diagramas Mermaid](#parte-20-documentación-viva-y-compilación-de-diagramas-mermaid)

---

## Parte 1: El Diagnóstico Inicial y la Observación de Cátedra

### Contexto y Problema Detectado
En la primera versión del sistema, el código sufría del antipatrón conocido como **Modelo de Dominio Anémico** (*Anemic Domain Model*), sumado a una violación del principio **Tell, Don't Ask** ("Decile al objeto qué hacer, no le preguntes sus datos para decidir vos").

La cátedra señaló las siguientes debilidades fundamentales:
1. **Contenedores de datos pasivos:** La clase `Usuario` era una entidad monolítica con una colección de datos (`nombre`, `email`, `rol`, etc.) y métodos estáticos (`@staticmethod`) que validaban strings o enums.
2. **Servicios hipertrofiados:** Los servicios de aplicación (`ServicioRequerimientos`, `ServicioUsuarios`) asumían toda la lógica de negocio mediante sentencias condicionales (`if rol == RolUsuario.SOLICITANTE`, `if rol in _ROLES_CON_EMAIL_CORPORATIVO`).
3. **Pérdida de la Orientación a Objetos:** En lugar de aprovechar el polimorfismo, el sistema consultaba el tipo/rol de un actor para tomar decisiones sobre él.

### El Antes vs. El Después Conceptual
* **Antes:** *"Servicio, decime el rol de este usuario. Si es técnico, preguntale si este requerimiento está asignado a su ID. Si ambas cosas son verdaderas, dejalo resolver."*
* **Después:** *"Requerimiento, quiero resolverte. Este es el usuario actor. Requerimiento le pide al actor: `actor.puede_resolver(self)`. Si el actor es un `Tecnico`, responde `self.id == req.tecnico_asignado_id`. Si es `Supervisor`, responde `True`. Si es `Solicitante`, responde `False`."*

---

## Parte 2: La Arquitectura General del Refactor (Opción B: Dominio Rico)

### Principios de Diseño Aplicados
1. **Information Expert (GRASP):** La responsabilidad de resolver una pregunta o validar una regla se asigna a la clase que posee la información necesaria para hacerlo.
2. **Polimorfismo:** Se sustituyen las sentencias condicionales dependientes del tipo por clases que implementan un contrato común.
3. **Doble Despacho (*Double Dispatch*):** Mecanismo de colaboración donde dos objetos polimórficos interactúan sin conocer los detalles de implementación mutuos.
4. **Encapsulamiento e Inmutabilidad:** Los datos críticos se protegen mediante propiedades de solo lectura y Value Objects inmutables.

### Diagrama Conceptual de Capas
```
┌─────────────────────────────────────────────────────────────┐
│                 PRESENTACIÓN (FastAPI)                      │
│ Routers reciben DTOs y pasan el `Usuario` autenticado       │
│ Dependencias usan `requerir_permiso(lambda u: u.puede_...`) │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│             SERVICIOS DE APLICACIÓN (Orquestación)          │
│ `ServicioRequerimientos`, `ServicioUsuarios`, etc.          │
│ Solo buscan entidades, llaman al dominio y persisten        │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    DOMINIO RICO                             │
│ • Jerarquía `Usuario` (Solicitante, Empleado, etc.)         │
│ • Jerarquía `Requerimiento` (Incidente, Solicitud)          │
│ • Value Objects (`Email`, `Comentario`, `Evento`)           │
│ • Fábricas (`FabricaUsuarios`, `FabricaRequerimientos`)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Parte 3: La Jerarquía de Usuarios — Clase Abstracta Raíz `Usuario`

### Ubicación: `app/usuarios/dominio/usuario.py`

### Propósito y Filosofía
La clase abstracta `Usuario` modela a cualquier persona registrada en la Mesa de Ayuda. Su diseño sigue el principio de **menor privilegio por defecto**:
* Todos los métodos que consultan permisos sobre requerimientos devuelven `False` en la clase base.
* Solo si una subclase sobreescribe explícitamente un método, dicho permiso existirá.

### Características Clave
1. **Constructor con Template Method:** Obliga a que cada subclase valide sus propias reglas de negocio mediante métodos protegidos abstractos:
   * `_exigir_email_admitido(email)`
   * `_exigir_suscripciones_admitidas(servicios)`
2. **Autenticación en el Dominio:** El método `autenticar(password, verificador)` reside en `Usuario`. La entidad decide *cuándo* una cuenta es apta para iniciar sesión (activa y con contraseña válida), mientras que la infraestructura solo provee la función de comparación de hashes (`bcrypt`).
3. **Discriminador de Rol:** La propiedad `rol` es abstracta. Devuelve un valor de `RolUsuario` únicamente para serialización, persistencia en MongoDB y claims de JWT, pero **nunca** para bifurcar flujos lógicos con `if`.

---

## Parte 4: La Invariante Corporativa — Clase Abstracta `Empleado`

### Ubicación: `app/usuarios/dominio/empleado.py`

### Jerarquía
```
Usuario (Abstracta)
└── Empleado (Abstracta)
    ├── Operador
    ├── Tecnico
    └── Supervisor
```

### Invariantes del Personal de la Cooperativa
En el diseño original, las restricciones del personal corporativo estaban dispersas en múltiples funciones estáticas. En el nuevo modelo, la clase intermedia `Empleado` centraliza estas tres reglas:
1. **Dominio Corporativo Obligatorio:** Todo empleado debe poseer un correo terminado en `@comunicarlos.com.ar`. Si se intenta construir un empleado con `@gmail.com` o similar, se lanza inmediatamente `EmailCorporativoRequeridoError`.
2. **Sin Servicios Suscriptos:** Los empleados no son clientes residenciales del sistema; por ende, su conjunto de servicios suscriptos debe estar obligatoriamente vacío.
3. **Visibilidad Global:** A diferencia del solicitante, todo empleado tiene acceso a la bandeja completa de tickets (`puede_ver(req) -> True`).

---

## Parte 5: Rol `Solicitante` — El Cliente y el Principio de Pertenencia

### Ubicación: `app/usuarios/dominio/solicitante.py`

### Reglas de Negocio del Solicitante
* Es el cliente residencial o comercial que abre incidentes y solicitudes.
* Puede usar cualquier proveedor de correo electrónico (Gmail, Hotmail, dominio propio, etc.).
* **Debe** contar con al menos un servicio activo de la cooperativa (`TELEFONIA_CELULAR`, `INTERNET_BANDA_ANCHA` o `TELEVISION`).

### Comportamiento Polimórfico
El `Solicitante` solo puede actuar sobre lo que le pertenece:
```python
def puede_ver(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.pertenece_a(self)

def puede_cerrar(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.pertenece_a(self)

def puede_cancelar(self, requerimiento: Requerimiento) -> bool:
    # Solo puede cancelar si es suyo y aún no comenzó su análisis
    return requerimiento.pertenece_a(self) and requerimiento.esta_abierto()

def puede_comentar(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.pertenece_a(self)
```
Observar cómo `Solicitante` le delega la pregunta de pertenencia al `Requerimiento`: no compara IDs por su cuenta.

---

## Parte 6: Rol `Operador` — Mesa de Entrada, Triage y Seguimiento

### Ubicación: `app/usuarios/dominio/operador.py`

### Responsabilidad de Negocio
El `Operador` es el personal de mesa de ayuda encargado de recepcionar los tickets, evaluarlos y asignarlos al área técnica correspondiente.

### Matriz de Capacidades
* **Inicio de Análisis:** `puede_iniciar_analisis(...) -> True`.
* **Asignación Técnica:** `puede_asignar_tecnico(...) -> True`.
* **Cierre y Cancelación:** Puede dar cierre de conformidad y cancelar tickets en cualquier estado previo a resolución.
* **Comentarios y Reaperturas:** Puede comentar tickets de cualquier solicitante. Además, `reabre_al_comentar() -> True`, lo que significa que si comenta un requerimiento en estado `RESUELTO`, este vuelve automáticamente a `EN_PROGRESO`.
* **Restricción Estricta:** No interviene en la solución técnica (`puede_iniciar_progreso` y `puede_resolver` devuelven `False`).
* **Auditoría:** `es_supervisable() -> True` (sus acciones generan eventos auditables para supervisores).

---

## Parte 7: Rol `Tecnico` — Responsabilidad de Resolución y Asignación Exclusiva

### Ubicación: `app/usuarios/dominio/tecnico.py`

### Responsabilidad de Negocio
El `Tecnico` es quien diagnostica y repara averías o ejecuta solicitudes en campo o de manera remota.

### Comportamiento Polimórfico Condicionado a la Asignación
El técnico no puede operar sobre cualquier ticket; su capacidad de acción está directamente ligada a que el requerimiento esté asignado a su persona:
```python
def puede_iniciar_progreso(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.esta_asignado_a(self)

def puede_resolver(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.esta_asignado_a(self)

def puede_derivar(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.esta_asignado_a(self)

def puede_comentar(self, requerimiento: Requerimiento) -> bool:
    return requerimiento.esta_asignado_a(self)
```
Además, define `puede_recibir_requerimientos() -> bool`, que devuelve `True` únicamente si su cuenta está en estado `activo`.

---

## Parte 8: Rol `Supervisor` — Autoridad Operativa y Capacidad de Supervisión

### Ubicación: `app/usuarios/dominio/supervisor.py`

### Responsabilidad de Negocio
El `Supervisor` es la máxima autoridad operativa dentro del sistema. Combina facultades extraordinarias sobre los tickets con labores de gestión de personal y auditoría.

### Capacidades Sobresalientes
1. **Control Total del Ciclo de Vida:** Puede ejecutar cualquier transición (`iniciar_analisis`, `asignar_tecnico`, `iniciar_progreso`, `resolver`, `cerrar`, `cancelar`), incluso sin ser el técnico asignado.
2. **Administración de Seguridad:** Es el único que posee `puede_administrar_usuarios() -> True` y `puede_administrar_supervisiones() -> True`.
3. **Receptor de Alertas:** `recibe_notificaciones() -> True`.
4. **Relación de Supervisión Activa:** Posee el método de negocio `supervisar(empleado)`. Antes de crear el vínculo, le pregunta al empleado `empleado.es_supervisable()`, evitando que un supervisor intente supervisar a un solicitante o a otro supervisor.

---

## Parte 9: El Patrón Factory Method — `FabricaUsuarios`

### Ubicación: `app/usuarios/dominio/fabrica.py`

### El Problema que Resuelve
Cuando un usuario llega desde la base de datos (MongoDB) o desde un formulario de creación HTTP, el rol viene expresado como un dato simple (`str` o `RolUsuario`). En algún lugar del sistema ese dato debe convertirse en una clase polimórfica.

### Implementación Canónica
```python
class FabricaUsuarios:
    _catalogo: dict[RolUsuario, type[Usuario]] = {
        RolUsuario.SOLICITANTE: Solicitante,
        RolUsuario.OPERADOR: Operador,
        RolUsuario.TECNICO: Tecnico,
        RolUsuario.SUPERVISOR: Supervisor,
    }

    @classmethod
    def crear(cls, rol: RolUsuario, **atributos: Any) -> Usuario:
        if not isinstance(rol, RolUsuario):
            raise TypeError("El rol debe ser una instancia de RolUsuario.")
        return cls._catalogo[rol](**atributos)
```
`FabricaUsuarios` es el **único lugar en toda la aplicación** donde un valor de `RolUsuario` se evalúa para seleccionar una clase. A partir de esa instancia, ningún servicio o router vuelve a consultar el rol para tomar decisiones.

---

## Parte 10: Value Object `Email` — Canonicidad e Inmutabilidad sin Excepciones

### Ubicación: `app/usuarios/dominio/email.py`

### De Método Estático a Value Object Real
En el sistema anterior, `Usuario.normalizar_email(str)` era un método estático que los servicios debían acordarse de invocar antes de buscar en la base de datos. Si un programador se olvidaba de llamarlo, `Ana.Perez@...` y `ana.perez@...` se trataban como cuentas distintas.

### Características del Value Object `Email`
1. **Inmutabilidad:** Utiliza `__slots__ = ("_valor",)` y no expone métodos mutadores.
2. **Normalización Garantizada:** En su constructor realiza `valor.strip().lower()`. Un objeto `Email` nunca puede existir en un estado no normalizado.
3. **Validación de Formato:** Aplica expresión regular contra correos inválidos.
4. **Igualdad Estructural:** Sobreescribe `__eq__` y `__hash__`, permitiendo comparar correos y usarlos como claves en diccionarios o conjuntos.

---

## Parte 11: Shared Kernel — `validaciones.py` y la Extinción de `@staticmethod`

### Ubicación: `app/compartido/validaciones.py`

### Filosofía del Cambio
Las validaciones de strings no vacíos o tipos de datos repetidas en `Incidente`, `Solicitud` y `Usuario` no eran lógica de negocio particular de ninguna de ellas, sino funciones puras de formateo.

### Funciones Centrales
* `texto_obligatorio(valor, campo, recortar=True)`: Verifica que el valor sea un string y no esté en blanco. Si falla por estar vacío, lanza `DatoInvalidoError` (que la API mapea automáticamente a HTTP 422).
* `instancia_de(valor, tipo, campo)`: Asegura que un argumento pertenezca exactamente a la clase o enum requerido.

Con esto, se erradicaron por completo los métodos `@staticmethod _validar_*` que antes sobrecargaban las entidades.

---

## Parte 12: Doble Despacho (*Double Dispatch*) entre `Requerimiento` y `Usuario`

### El Concepto
El doble despacho es una técnica donde una operación depende de los tipos concretos de dos objetos sin necesidad de hacer type-casting o usar sentencias `isinstance` / `if rol == ...`.

### Mecánica de Interacción
Tomemos la operación de cierre de conformidad (`cerrar`):
```
[ServicioRequerimientos]
       │
       │  cerrar(actor)
       ▼
[Requerimiento]
       │
       │  1. ¿Estado es RESUELTO? (Validación interna del ticket)
       │  2. actor.puede_cerrar(self)
       ▼
   [Usuario (Actor)] ◄─── Puede ser Solicitante, Operador, Tecnico, Supervisor
       │
       │  (Si es Solicitante):
       │  requerimiento.pertenece_a(self)
       ▼
[Requerimiento]
       │
       │  Responde True si self.solicitante_id == self.id
       ▼
Resultado de Permiso Concedido / Denegado
```
Ninguna clase espía los atributos privados de la otra. `Requerimiento` delega el permiso en `actor`, y `actor` delega la comprobación de autoría en `Requerimiento`.

---

## Parte 13: Transiciones de Estado en `Requerimiento` — Desaparición de `(autor_id, rol_actor)`

### Comparativa de Código

#### Código Anterior (Acoplado y Frágil):
```python
# ANTES: Se requerían IDs y strings de rol sueltos
def iniciar_analisis(self, autor_id: uuid.UUID, rol_actor: RolUsuario) -> EventoRequerimiento:
    self._exigir_estado(EstadoRequerimiento.ABIERTO)
    self._exigir_rol(rol_actor, _ROLES_ASIGNACION, "iniciar el análisis")
    self.estado = EstadoRequerimiento.EN_ANALISIS
    ...
```

#### Código Actual (Limpio y Polimórfico):
```python
# AHORA: Se recibe la entidad de dominio completa
def iniciar_analisis(self, actor: Usuario) -> EventoRequerimiento:
    self._exigir_estado(EstadoRequerimiento.ABIERTO)
    self._exigir_permiso(actor.puede_iniciar_analisis(self), actor, "iniciar el análisis")
    self.estado = EstadoRequerimiento.EN_ANALISIS
    return self._registrar_evento(
        tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
        autor_id=actor.id,
        detalle="Estado cambiado de ABIERTO a EN_ANALISIS.",
    )
```
Se aplicó este mismo cambio a:
* `iniciar_progreso(actor)`
* `asignar_tecnico(tecnico, actor)`
* `resolver(nota_resolucion, actor)`
* `cerrar(actor)`
* `cancelar(actor)`
* `agregar_comentario(texto, actor)`
* `derivar_interconsulta(tecnico_destino, actor)`

---

## Parte 14: Validación de Destinatarios de Asignación e Interconsulta en el Dominio

### El Defecto Previo en la Capa de Servicio
En la implementación anterior, el servicio contenía un método privado llamado `_exigir_tecnico_valido(tecnico_id)`. Dicho método realizaba consultas directas al repositorio de usuarios e inspeccionaba con `if tecnico.rol != RolUsuario.TECNICO` y `if not tecnico.activo`.

### El Nuevo Enfoque de Dominio
Ahora, el servicio simplemente recupera la entidad `Usuario` destinataria del repositorio (validando solo su existencia física) y se la entrega al `Requerimiento`.

El `Requerimiento` le exige al técnico:
```python
def _exigir_que_pueda_recibirlo(self, tecnico: Usuario) -> None:
    if not tecnico.puede_recibir_requerimientos():
        raise TecnicoInvalidoError(
            f"El usuario '{tecnico.id}' no puede recibir requerimientos: "
            "debe ser un Técnico y estar activo."
        )
```
Cada subclase de `Usuario` sabe si puede recibir tickets:
* `Solicitante`, `Operador`, `Supervisor` responden `False`.
* `Tecnico` responde `self.activo`.

---

## Parte 15: Servicios de Aplicación Anoréxicos — Orquestación Pura y `_aplicar_transicion`

### La Regla de Oro de los Servicios en DDD
Un servicio de aplicación **no debe tomar decisiones de negocio ni ejecutar cálculos de reglas**. Su única función es:
1. Abrir transacciones / recuperar agregados del repositorio.
2. Invocar métodos del dominio.
3. Persistir las modificaciones.
4. Despachar eventos de dominio a los observadores.

### El Helper Genérico `_aplicar_transicion`
En `ServicioRequerimientos`, todas las transiciones del ciclo de vida fueron unificadas a través de una función de orden superior:
```python
def _aplicar_transicion(
    self,
    requerimiento_id: uuid.UUID,
    transicion: Callable[[Requerimiento], EventoRequerimiento],
) -> Requerimiento:
    requerimiento = self._buscar_o_lanzar(requerimiento_id)
    evento = transicion(requerimiento)
    self._repositorio.guardar(requerimiento)
    self._despachador.notificar(evento)
    return requerimiento
```
Gracias a esto, métodos como `iniciar_analisis`, `resolver` o `cerrar` se reducen a una sola línea limpia y legible.

---

## Parte 16: Dominio de Supervisión y Notificaciones con Comportamiento Activo

### `RelacionSupervision` (`app/supervision/dominio.py`)
Antes era un simple struct de datos con dos UUIDs. Ahora cuenta con lógica propia:
* `audita_a(usuario_id) -> bool`: Sabe determinar si un evento pertenece a su supervisado.
* `notificar(evento) -> Notificacion`: Transforma directamente un `EventoRequerimiento` en una `Notificacion` dirigida a su supervisor, garantizando que un supervisor nunca reciba notificaciones de empleados que no tiene a cargo.

### `Notificacion` (`app/notificaciones/dominio.py`)
* `marcar_leida_por(supervisor_id)`: Valida la identidad del supervisor antes de cambiar el estado de lectura. Si un supervisor intenta marcar una notificación ajena, se responde con un error de entidad no encontrada, protegiendo la confidencialidad de la información.

---

## Parte 17: Seguridad y Presentación en FastAPI — De `requerir_rol` a `requerir_permiso`

### La Vulnerabilidad del Acoplamiento en Rutas
Antes, los endpoints de la API utilizaban dependencias del estilo:
```python
# ANTES: Acoplado al enum de roles
@router.post("/supervisar", dependencies=[Depends(requerir_rol(RolUsuario.SUPERVISOR))])
```
Esto obligaba a los routers a conocer qué roles podían hacer qué cosas, duplicando las reglas del dominio en la capa HTTP.

### El Nuevo Helper `requerir_permiso`
En [`app/deps.py`](app/deps.py), se reemplazó por un esquema basado en predicados polimórficos:
```python
def requerir_permiso(tiene_permiso: Callable[[Usuario], bool]) -> Callable[[Usuario], Usuario]:
    def verificar(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:
        if not tiene_permiso(usuario_actual):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{usuario_actual.rol.value}' no tiene acceso a esta operación.",
            )
        return usuario_actual
    return verificar
```

En las rutas, ahora se declara:
```python
# AHORA: Pregunta por capacidades, no por etiquetas
@router.post("/supervisar", dependencies=[Depends(requerir_permiso(lambda u: u.puede_administrar_supervisiones()))])
```

---

## Parte 18: Hallazgos Críticos Corregidos en la Revisión `xhigh`

Durante la revisión profunda del refactor, se detectaron y subsanaron 7 problemas clave:

1. **Error 500 en Login por Formato de Email:** Si un usuario intentaba autenticarse con un email sin formato (ej. `"lucia@gmail"`), el Value Object `Email` lanzaba un `ValueError` no atrapado que devolvía HTTP 500. Se capturó adecuadamente para responder **HTTP 401 Unauthorized**.
2. **Textos con Espacios en Blanco:** Un título como `"   "` causaba error de servidor 500. Se introdujo `DatoInvalidoError`, transformándolo en **HTTP 422 Unprocessable Entity**.
3. **Listado Ineficiente de Solicitantes:** Para listar los tickets de un solicitante, el sistema traía todos los requerimientos de la base a memoria y filtraba con Python. Se refactorizó con `actor.requerimientos_visibles(repo)`: el `Solicitante` delega en `repo.listar_por_solicitante(id)` usando el índice nativo de MongoDB.
4. **Hashes de Contraseña Íntegros:** Se eliminó el `.strip()` accidental sobre los hashes de contraseñas de bcrypt, preservando su contenido binario exacto.
5. **Reutilización de Consultas Técnicas:** La capacidad `puede_consultar_tecnicos` se elevó a la clase `Empleado`, eliminando código repetido en `Operador`, `Tecnico` y `Supervisor`.

---

## Parte 19: La Suite de Pruebas Automatizadas — De 257 a 372 Tests

### El Crecimiento de las Pruebas
La suite creció en **115 tests unitarios y de integración**:
* Se pasó de 257 tests iniciales a 360 en el refactor base, y luego a **372 tests** tras la revisión exhaustiva.
* Todos los tests corren en menos de 50 segundos.

### Especificación de la Matriz de Roles (`tests/test_usuarios_dominio.py`)
En lugar de tests genéricos, se creó una clase de prueba específica por cada rol:
* `TestSolicitante`: Prueba exhaustiva de lo que puede hacer sobre sus tickets propios y la imposibilidad de tocar tickets ajenos.
* `TestOperador`: Prueba de triage, asignaciones y reapertura de tickets al comentar.
* `TestTecnico`: Prueba de resolución y derivación condicionadas a ser el técnico asignado.
* `TestSupervisor`: Prueba de facultades plenas y supervisión de empleados.
* `TestEmail`: Prueba de normalización e inmutabilidad del Value Object.

---

## Parte 20: Documentación Viva y Compilación de Diagramas Mermaid

### Sincronización entre Código y Arquitectura
Uno de los puntos más delicados en una entrega académica es la consistencia entre los diagramas y el código final. 

### Mejoras Realizadas en los Diagramas
1. **`diagrama_clases.mmd`:**
   * Modela la jerarquía completa: `Usuario` $\rightarrow$ `Solicitante` / `Empleado` $\rightarrow$ `Operador`, `Tecnico`, `Supervisor`.
   * Incluye `FabricaUsuarios` y el Value Object `Email`.
   * Muestra las firmas de métodos con `actor: Usuario` y las aristas de doble despacho.
2. **`diagrama_secuencia.mmd`:**
   * Muestra el ciclo interactivo de resolución con `actor.puede_resolver(req)` y `req.esta_asignado_a(actor)`.
3. **`compilar_mermaid.py`:**
   * Script en Python creado para compilar los archivos `.mmd` a visores interactivos `.html` puros (sin dependencias externas).
   * Corrige un bug visual previo donde entidades clave quedaban clasificadas en una columna "Otros Componentes".

---

### Resumen para el Oyente / Lector de NotebookLM
El refactor convirtió un código de estilo procedimental disfrazado de clases en una arquitectura orientada a objetos pura de nivel profesional. Las entidades ahora toman sus propias decisiones, los servicios orquestan sin interferir, los tipos de datos protegen el sistema por construcción y la suite de pruebas garantiza que ninguna regla de negocio pueda romperse inadvertidamente.

