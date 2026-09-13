# 🏛️ 03 — Arquitectura y Patrones de Diseño

`[⬅️ Anterior: 02_OBJETIVO_Y_DOMINIO_NEGOCIO.md](02_OBJETIVO_Y_DOMINIO_NEGOCIO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 04_MODULOS_Y_ESTRUCTURA_CODIGO.md](04_MODULOS_Y_ESTRUCTURA_CODIGO.md)`

---

## 1. Arquitectura Hexagonal / en Capas

El núcleo del sistema sigue una separación concéntrica estricta donde **las dependencias siempre apuntan hacia adentro**:

```
┌──────────────────────────────────────────────────────────┐
│ 1. PRESENTACIÓN (Routers FastAPI, Schemas Pydantic)      │
│    ┌──────────────────────────────────────────────────┐  │
│    │ 2. APLICACIÓN (Servicios de Caso de Uso)          │  │
│    │    ┌──────────────────────────────────────────┐  │  │
│    │    │ 3. DOMINIO (Entidades, Interfaces, Reglas)│  │  │
│    │    └──────────────────────────────────────────┘  │  │
│    └──────────────────────────────────────────────────┘  │
│ 4. INFRAESTRUCTURA (PyMongo, Bcrypt, JWT, Red)           │
└──────────────────────────────────────────────────────────┘
```

* **Regla de Oro**: La capa de **Dominio no conoce a nadie**. No tiene imports de FastAPI, Pydantic, PyMongo ni bibliotecas externas. Solo usa tipos estándar de Python.
* **Infraestructura** implementa los puertos definidos en el Dominio (inversión de dependencias).

---

## 2. Patrones de Diseño Clave

### A. Repositorio Abstracto (Dependency Inversion Principle)
En lugar de que los servicios llamen a la base de datos directamente, interactúan con un contrato abstracto:

```python
# app/requerimientos/repositorio.py (Capa de Dominio)
from abc import ABC, abstractmethod
from app.requerimientos.dominio import Requerimiento

class RepositorioRequerimientos(ABC):
    @abstractmethod
    def guardar(self, req: Requerimiento) -> None: ...
    
    @abstractmethod
    def buscar_por_id(self, req_id: str) -> Requerimiento | None: ...
```

* **Ventaja**: Permite cambiar la persistencia (de SQLite a MongoDB o Postgres) o crear repositorios en memoria (`FakeRepositorio`) para tests unitarios que corren en milisegundos.

### B. Patrón Observer para Notificaciones
El dominio emite eventos ante cambios relevantes sin saber quién los escucha:

```python
# app/notificaciones/despachador.py
class DespachadorEventos:
    def suscribir(self, observador: ObservadorRequerimiento) -> None: ...
    def notificar(self, evento: EventoRequerimiento) -> None: ...
```

> **Nota**: `DespachadorEventos` se construye **por request** (`app/deps.py`), no como singleton de módulo: el observer `ObservadorNotificacionesMongo` (genera una `Notificacion` real por cada supervisor de un empleado que generó el evento) necesita el `db` de la request actual para consultar `RepositorioSupervision`. Sigue siendo el mismo patrón Observer — solo cambia el scope de vida del Sujeto, que nunca lo exige singleton.

### C. Shared Kernel Mínimo (`RolUsuario`, `ServicioComunicarlos`)
Para evitar importaciones circulares entre `usuarios` y `requerimientos`, los tipos comunes del negocio se centralizan en `app/compartido/dominio.py`.

---

## 3. Flujo de Control vs Flujo de Dependencia

```
Petición HTTP  ──►  Router  ──►  Servicio  ──►  Entidad Dominio
                      │            │                    ▲
                      ▼            ▼                    │
                   Schemas     Llama método        (Implementa)
                  Pydantic     Repositorio              │
                                   │                    │
                                   ▼                    │
                              Interfaz Repo ◄───────────┘
                                   ▲
                                   │ (Inversión)
                              PyMongo Repo (Infraestructura)
```

---

## 4. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Consulta las implementaciones canónicas de estos y otros patrones en:
* [`BuenasPracticasenPython/06_patron_factory_method.md`](BuenasPracticasenPython/06_patron_factory_method.md): Factory para crear instancias de `Incidente` o `Solicitud` según el tipo.
* [`BuenasPracticasenPython/07_patron_strategy.md`](BuenasPracticasenPython/07_patron_strategy.md): Estrategias intercambiables de cálculo de SLA o asignación automática de técnicos.
* [`BuenasPracticasenPython/08_patron_observer.md`](BuenasPracticasenPython/08_patron_observer.md): Suscripción y despacho 1 a N de eventos de tickets.
* [`BuenasPracticasenPython/05_patron_singleton.md`](BuenasPracticasenPython/05_patron_singleton.md): Instancia única de configuración global o cliente de conexión.
* [`BuenasPracticasenPython/09_patrones_adapter_y_decorator.md`](BuenasPracticasenPython/09_patrones_adapter_y_decorator.md): Adaptadores para APIs externas y decoradores de logging/auditoría.

---

`[⬅️ Anterior: 02_OBJETIVO_Y_DOMINIO_NEGOCIO.md](02_OBJETIVO_Y_DOMINIO_NEGOCIO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 04_MODULOS_Y_ESTRUCTURA_CODIGO.md](04_MODULOS_Y_ESTRUCTURA_CODIGO.md)`
