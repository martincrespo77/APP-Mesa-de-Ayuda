# 📑 Índice y Guía de Lectura de Contexto

Bienvenido al repositorio de contexto del sistema **Mesa de Ayuda — Cooperativa Comunicarlos** (Proyecto PP5 / FIE).

Este directorio contiene la información técnica, de arquitectura, de dominio y de infraestructura organizada de manera **jerárquica y paginada**. Está diseñada específicamente para que modelos de lenguaje (como Claude) o desarrolladores puedan inicializar o reconstruir este sistema desde cero en un nuevo repositorio sin saturar su ventana de contexto.

---

## 🧭 Regla de Consumo de Contexto (< 200 Líneas)

> [!IMPORTANT]
> **Para Agentes de IA / Claude**: Cada documento de esta serie tiene deliberadamente **menos de 200 líneas**. No leas todos los documentos a la vez. Lee un documento según la fase de trabajo en la que te encuentres, procesa la información y avanza secuencialmente usando los enlaces de navegación inferior y superior.

---

## 📚 Mapa Jerárquico de Documentos Principales

| # | Documento | Propósito Principal |
|:---:|:---|:---|
| **01** | [`01_STACK_TECNOLOGICO.md`](01_STACK_TECNOLOGICO.md) | Definición formal del stack tecnológico completo, versiones y herramientas. |
| **02** | [`02_OBJETIVO_Y_DOMINIO_NEGOCIO.md`](02_OBJETIVO_Y_DOMINIO_NEGOCIO.md) | Enunciado de negocio, tipos de requerimientos, roles y ciclo de vida de estados. |
| **03** | [`03_ARQUITECTURA_Y_PATRONES.md`](03_ARQUITECTURA_Y_PATRONES.md) | Arquitectura Hexagonal / en Capas, Dominio puro, Observer e Inversión de Dependencias. |
| **04** | [`04_MODULOS_Y_ESTRUCTURA_CODIGO.md`](04_MODULOS_Y_ESTRUCTURA_CODIGO.md) | Árbol de carpetas canónico, contratos entre capas y anatomía de un módulo. |
| **05** | [`05_CLIENTE_DESCRITORIO_PYQT6.md`](05_CLIENTE_DESCRITORIO_PYQT6.md) | Frontend de escritorio en PyQt6, ApiClient desacoplado y Modo Demostración. |
| **06** | [`06_INFRAESTRUCTURA_Y_PERSISTENCIA.md`](06_INFRAESTRUCTURA_Y_PERSISTENCIA.md) | MongoDB (PyMongo), colecciones, Dockerfile, Docker Compose y variables `.env`. |
| **07** | [`07_TESTING_CALIDAD_Y_CONVENCIONES.md`](07_TESTING_CALIDAD_Y_CONVENCIONES.md) | Estrategia de testing (Pytest, Mongomock), calidad (Ruff, Mypy) y convenciones. |
| **08** | [`08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md`](08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md) | Secuencia paso a paso para construir el proyecto desde cero en un repo nuevo. |

---

## 🏛️ Biblioteca de Buenas Prácticas y Patrones de Diseño

El subdirectorio [`BuenasPracticasenPython/`](BuenasPracticasenPython/README.md) contiene 15 guías normativas de cátedra con ejemplos de código aplicables:

* **Fundamentos POO y Dominio**: [`01_principios_poo_booch.md`](BuenasPracticasenPython/01_principios_poo_booch.md), [`02_separacion_responsabilidades_expert.md`](BuenasPracticasenPython/02_separacion_responsabilidades_expert.md), [`04_manejo_excepciones_y_validaciones.md`](BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md).
* **Modularidad Física**: [`03_modularidad_archivos_entidades.md`](BuenasPracticasenPython/03_modularidad_archivos_entidades.md) (una entidad por archivo).
* **Patrones Creacionales**: [`05_patron_singleton.md`](BuenasPracticasenPython/05_patron_singleton.md), [`06_patron_factory_method.md`](BuenasPracticasenPython/06_patron_factory_method.md).
* **Patrones de Comportamiento**: [`07_patron_strategy.md`](BuenasPracticasenPython/07_patron_strategy.md), [`08_patron_observer.md`](BuenasPracticasenPython/08_patron_observer.md).
* **Patrones Estructurales**: [`09_patrones_adapter_y_decorator.md`](BuenasPracticasenPython/09_patrones_adapter_y_decorator.md).
* **Testing y Calidad**: [`10_unit_testing_buenas_practicas.md`](BuenasPracticasenPython/10_unit_testing_buenas_practicas.md), [`14_estandares_python_moderno.md`](BuenasPracticasenPython/14_estandares_python_moderno.md).
* **Arquitectura y Persistencia**: [`11_arquitectura_en_capas_api.md`](BuenasPracticasenPython/11_arquitectura_en_capas_api.md), [`12_patron_repository_y_persistencia.md`](BuenasPracticasenPython/12_patron_repository_y_persistencia.md), [`13_serializacion_polimorfica.md`](BuenasPracticasenPython/13_serializacion_polimorfica.md).

---

## 🎯 Orden Recomendado de Lectura

1. Si vas a **iniciar el proyecto desde cero**:
   * Comienza leyendo `01_STACK_TECNOLOGICO.md` y `02_OBJETIVO_Y_DOMINIO_NEGOCIO.md`.
   * Continúa con `03_ARQUITECTURA_Y_PATRONES.md` y `04_MODULOS_Y_ESTRUCTURA_CODIGO.md` antes de escribir código.
   * Consulta `08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md` como hoja de ruta paso a paso.
2. Si vas a trabajar en la **persistencia o base de datos**:
   * Consulta `06_INFRAESTRUCTURA_Y_PERSISTENCIA.md` y apóyate en [`12_patron_repository_y_persistencia.md`](BuenasPracticasenPython/12_patron_repository_y_persistencia.md) y [`13_serializacion_polimorfica.md`](BuenasPracticasenPython/13_serializacion_polimorfica.md).
3. Si vas a desarrollar o extender la **interfaz gráfica**:
   * Consulta `05_CLIENTE_DESCRITORIO_PYQT6.md`.
4. Si vas a crear **tests o auditar calidad**:
   * Consulta `07_TESTING_CALIDAD_Y_CONVENCIONES.md` y apóyate en [`10_unit_testing_buenas_practicas.md`](BuenasPracticasenPython/10_unit_testing_buenas_practicas.md).

---

**Navegación:**
`[📑 Índice]` | **`[Siguiente ➡️: 01_STACK_TECNOLOGICO.md](01_STACK_TECNOLOGICO.md)`**
