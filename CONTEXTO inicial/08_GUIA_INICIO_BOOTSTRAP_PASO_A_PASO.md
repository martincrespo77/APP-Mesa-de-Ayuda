# 🚀 08 — Guía de Inicio y Bootstrap Paso a Paso

`[⬅️ Anterior: 07_TESTING_CALIDAD_Y_CONVENCIONES.md](07_TESTING_CALIDAD_Y_CONVENCIONES.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)`

---

## 1. Hoja de Ruta para un Repositorio Nuevo

Si estás comenzando este proyecto desde cero en un repositorio vacío, sigue estrictamente esta secuencia por capas (de adentro hacia afuera) para mantener la arquitectura limpia y evitar retrabajo:

```
Paso 1: Entorno (uv + pyproject.toml)
  └── Paso 2: Dominio Puro y Shared Kernel (+ tests unitarios)
        └── Paso 3: Repositorios Abstractos y Servicios (+ tests con fakes)
              └── Paso 4: Presentación (Pydantic, Routers, Auth JWT)
                    └── Paso 5: Persistencia con PyMongo (+ mongomock)
                          └── Paso 6: Cliente de Escritorio PyQt6 (+ Modo Demo)
                                └── Paso 7: Docker Compose y Colección Bruno
```

---

## 2. Ejecución Secuencial Detallada

### Paso 1: Configurar el Entorno con `uv`
1. Inicializar el proyecto con Python 3.12:
   ```bash
   uv init --name mesa-de-ayuda-comunicarlos
   ```
2. Reemplazar `pyproject.toml` con las dependencias especificadas en [`01_STACK_TECNOLOGICO.md`](01_STACK_TECNOLOGICO.md).
3. Sincronizar dependencias: `uv sync`.
* *Referencia*: [`BuenasPracticasenPython/14_estandares_python_moderno.md`](BuenasPracticasenPython/14_estandares_python_moderno.md).

### Paso 2: Crear el Shared Kernel y el Dominio Puro
1. Crear `app/compartido/dominio.py` con el enum `RolUsuario`.
2. Crear `app/usuarios/dominio.py` con la entidad `Usuario` y reglas de contraseña/estado.
3. Crear `app/requerimientos/dominio.py` con `Requerimiento`, `Incidente`, `Solicitud` y transiciones de estado.
4. Escribir y validar tests unitarios con `pytest` aplicando el patrón AAA.
* *Referencias*: [`BuenasPracticasenPython/01_principios_poo_booch.md`](BuenasPracticasenPython/01_principios_poo_booch.md), [`02_separacion_responsabilidades_expert.md`](BuenasPracticasenPython/02_separacion_responsabilidades_expert.md), [`03_modularidad_archivos_entidades.md`](BuenasPracticasenPython/03_modularidad_archivos_entidades.md) y [`04_manejo_excepciones_y_validaciones.md`](BuenasPracticasenPython/04_manejo_excepciones_y_validaciones.md).

### Paso 3: Definir Repositorios Abstractos y Servicios
1. Crear interfaces abstractas (`ABC`) en `app/usuarios/repositorio.py` y `app/requerimientos/repositorio.py`.
2. Implementar `app/notificaciones/dominio.py` con el patrón Observer para eventos de requerimientos.
3. Crear `servicios.py` en cada módulo orquestando los casos de uso.
4. Probar servicios usando implementaciones en memoria (`FakeRepositorio`).
* *Referencias*: [`BuenasPracticasenPython/06_patron_factory_method.md`](BuenasPracticasenPython/06_patron_factory_method.md), [`07_patron_strategy.md`](BuenasPracticasenPython/07_patron_strategy.md) y [`08_patron_observer.md`](BuenasPracticasenPython/08_patron_observer.md).

### Paso 4: Construir la Capa de Presentación (FastAPI)
1. Definir esquemas Pydantic v2 en `schemas.py` para cada módulo.
2. Implementar `app/auth.py` (JWT y hashing bcrypt) y `app/config.py` con Pydantic Settings.
3. Crear `app/deps.py` para inyección de dependencias (`obtener_usuario_actual`, etc.).
4. Montar los routers (`router.py`) en `main.py` y comprobar Swagger en `http://localhost:8000/docs`.
* *Referencia*: [`BuenasPracticasenPython/11_arquitectura_en_capas_api.md`](BuenasPracticasenPython/11_arquitectura_en_capas_api.md).

### Paso 5: Implementar Persistencia en MongoDB
1. Crear `app/infraestructura/database.py` gestionando la conexión PyMongo en el lifespan.
2. Crear adaptadores `repo_usuarios.py` y `repo_requerimientos.py` traduciendo diccionarios BSON a entidades.
3. Validar con tests de integración usando `mongomock` en `tests/test_infraestructura.py`.
* *Referencias*: [`BuenasPracticasenPython/12_patron_repository_y_persistencia.md`](BuenasPracticasenPython/12_patron_repository_y_persistencia.md) y [`13_serializacion_polimorfica.md`](BuenasPracticasenPython/13_serializacion_polimorfica.md).

### Paso 6: Desarrollar el Frontend en PyQt6
1. Crear `desktop/api_client.py` con soporte para conexión real y datos sintéticos (`--demo`).
2. Diseñar las vistas en `desktop/views/login_window.py` y `desktop/views/main_window.py`.
3. Aplicar el tema oscuro en `desktop/styles.py` y conectar eventos Qt.
* *Detalles en*: [`05_CLIENTE_DESCRITORIO_PYQT6.md`](05_CLIENTE_DESCRITORIO_PYQT6.md).

### Paso 7: Dockerización, Bruno y Calidad
1. Crear `Dockerfile` y `docker-compose.yml` vinculando la API y `mongo:7`.
2. Crear la colección de requests en `bruno/` para verificar los flujos completos.
3. Ejecutar suite de pruebas y linters (`pytest`, `ruff check`, `mypy`).
* *Referencia*: [`BuenasPracticasenPython/10_unit_testing_buenas_practicas.md`](BuenasPracticasenPython/10_unit_testing_buenas_practicas.md).

---

## 3. Checklist de Comprobación Final

* [ ] `uv run pytest` pasa el 100% de los tests con patrón AAA.
* [ ] `uv run ruff check .` no arroja advertencias de formato ni linting.
* [ ] `uv run mypy app/ desktop/` confirma tipado estático válido.
* [ ] `uv run python -m desktop.main --demo` abre la GUI inmediatamente sin backend.
* [ ] `docker compose up --build` levanta el sistema y responde en `http://localhost:8000/health`.

---

`[⬅️ Anterior: 07_TESTING_CALIDAD_Y_CONVENCIONES.md](07_TESTING_CALIDAD_Y_CONVENCIONES.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)`
