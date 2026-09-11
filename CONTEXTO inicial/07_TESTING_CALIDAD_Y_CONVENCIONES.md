# 🧪 07 — Testing, Calidad y Convenciones

`[⬅️ Anterior: 06_INFRAESTRUCTURA_Y_PERSISTENCIA.md](06_INFRAESTRUCTURA_Y_PERSISTENCIA.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md](08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md)`

---

## 1. Estrategia de Testing (Pirámide de Pruebas)

El proyecto cuenta con una cobertura integral organizada en capas independientes:

```
                  ┌─────────────────────┐
                  │ Tests Integración   │ (TestClient / Routers / Bruno)
                  ├─────────────────────┤
                  │ Tests Infra / BD    │ (Mongomock en memoria)
                  ├─────────────────────┤
                  │ Tests de Servicios  │ (Fakes en memoria)
                  ├─────────────────────┤
                  │  Tests de Dominio   │ (POO pura, sin dependencias)
                  └─────────────────────┘
```

1. **Tests de Dominio (`test_*_dominio.py`)**: Validan que las reglas de negocio, transiciones prohibidas de estado y permisos de roles fallen o tengan éxito exactamente según la especificación, sin tocar disco ni base de datos.
2. **Tests de Servicios (`test_*_servicios.py`)**: Utilizan `FakeRepositorio` (implementaciones en memoria con diccionarios de Python) para probar casos de uso en milisegundos.
3. **Tests de Infraestructura (`test_infraestructura.py`)**: Utilizan `mongomock` para validar que las consultas, filtros BSON e inserciones se comporten como en una base de datos real.
4. **Tests de Desktop (`test_desktop_client.py`)**: Validan el comportamiento del `ApiClient`, decodificación de tokens y el Modo Demo.

### Ejecución de Tests:
```bash
# Correr toda la suite
uv run pytest

# Correr tests con reporte condensado
uv run pytest -q

# Correr un archivo de prueba específico
uv run pytest tests/test_requerimientos_dominio.py
```

---

## 2. Herramientas de Calidad de Código

### A. Linter y Formateador: **Ruff**
Configurado en `pyproject.toml` con longitud máxima de 100 caracteres por línea:
```bash
# Revisar errores de estilo
uv run ruff check .

# Corregir errores y ordenar imports automáticamente
uv run ruff check --fix .
uv run ruff format .
```

### B. Verificación Estática de Tipos: **Mypy**
Tipado estricto en Python 3.12:
```bash
uv run mypy app/ desktop/
```

---

## 3. Convenciones de Código y Buenas Prácticas

* **Idioma del Dominio**: Nombres de clases y modelos en español (`RolUsuario`, `Requerimiento`, `Incidente`, `Solicitud`) para fidelidad con el lenguaje del cliente/negocio.
* **Nomenclatura Técnica**: `snake_case` para funciones y métodos; `PascalCase` para clases y excepciones.
* **Conventional Commits**: Mensajes con prefijo descriptivo:
  * `feat:` nueva funcionalidad.
  * `fix:` corrección de error.
  * `refactor:` refactorización interna sin cambio de comportamiento.
  * `docs:` cambios exclusivamente en documentación.
  * `test:` adición o ajuste de pruebas.

---

## 4. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Para estándares exhaustivos de pruebas y tipado moderno:
* [`BuenasPracticasenPython/10_unit_testing_buenas_practicas.md`](BuenasPracticasenPython/10_unit_testing_buenas_practicas.md): Implementación rigurosa del patrón AAA (Arrange-Act-Assert), uso de mocks e invariantes aislados.
* [`BuenasPracticasenPython/14_estandares_python_moderno.md`](BuenasPracticasenPython/14_estandares_python_moderno.md): Convenciones de tipado estático, gestión hermética con `uv` y empaquetado multi-stage.

---

`[⬅️ Anterior: 06_INFRAESTRUCTURA_Y_PERSISTENCIA.md](06_INFRAESTRUCTURA_Y_PERSISTENCIA.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md](08_GUIA_INICIO_BOOTSTRAP_PASO_A_PASO.md)`
