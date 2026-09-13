# 📂 04 — Módulos y Estructura del Código

`[⬅️ Anterior: 03_ARQUITECTURA_Y_PATRONES.md](03_ARQUITECTURA_Y_PATRONES.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 05_CLIENTE_DESCRITORIO_PYQT6.md](05_CLIENTE_DESCRITORIO_PYQT6.md)`

---

## 1. Árbol de Directorios del Proyecto

```
.
├── app/                        # Núcleo del Backend (FastAPI + Dominio)
│   ├── compartido/             # Shared Kernel (RolUsuario, ServicioComunicarlos)
│   ├── usuarios/               # Módulo de Usuarios y Autenticación
│   ├── requerimientos/         # Módulo de Incidentes y Solicitudes
│   ├── supervision/            # Relación N:M Supervisor <-> Operador/Técnico
│   ├── notificaciones/         # Patrón Observer + entidad Notificacion persistida
│   ├── infraestructura/        # Conectores PyMongo y Repositorios
│   ├── auth.py                 # Lógica JWT y hashing bcrypt
│   ├── config.py               # Configuración tipada (.env)
│   └── deps.py                 # Inyección de dependencias FastAPI
├── desktop/                    # Frontend de escritorio independiente (PyQt6)
│   ├── api_client.py           # Cliente HTTP desacoplado + Modo Demo
│   ├── styles.py               # Hoja de estilos QSS oscura
│   ├── main.py                 # Punto de entrada GUI
│   └── views/                  # Vistas (LoginWindow, MainWindow)
├── tests/                      # Suite completa de pruebas con Pytest
├── bruno/                      # Colección de requests API
├── infra/                      # Configuración de Docker y Caddy
├── docker-compose.yml          # Orquestación de API + MongoDB
├── pyproject.toml              # Dependencias y herramientas
└── main.py                     # Instancia FastAPI y punto de entrada API
```

---

## 2. Anatomía de un Módulo de Negocio

Cada módulo funcional dentro de `app/` (`usuarios/`, `requerimientos/`) respeta el mismo patrón de 6 archivos:

| Archivo | Capa | Responsabilidad |
|---|---|---|
| `dominio.py` | Dominio | Entidades puras, métodos de negocio, invariantes y validaciones de estado. |
| `excepciones.py` | Dominio | Errores específicos del negocio (ej. `RequerimientoNoEncontradoError`). |
| `repositorio.py` | Dominio | Interfaces abstractas (`ABC`) que definen el contrato de persistencia. |
| `servicios.py` | Aplicación | Orquestación de casos de uso (crear, asignar, resolver, emitir eventos). |
| `schemas.py` | Presentación | Modelos Pydantic v2 para serializar/deserializar requests y responses JSON. |
| `router.py` | Presentación | Endpoints FastAPI (`@router.post`, etc.), códigos HTTP y uso de `deps.py`. |

`supervision/` y `notificaciones/` (a partir de la entidad `Notificacion` persistida) siguen el mismo patrón de 6 archivos. `requerimientos/dominio/` es un subpaquete (una entidad por archivo): `base.py`, `incidente.py`, `solicitud.py`, `comentario.py`, `estados.py`.

---

## 3. Responsabilidades de Archivos Raíz de `app/`

* **`app/config.py`**: Clase `Settings` basada en `pydantic_settings.BaseSettings`. Lee y valida variables obligatorias: `SECRET_KEY`, `MONGODB_URL`, `MONGODB_DB_NAME`.
* **`app/auth.py`**: Funciones utilitarias para generar tokens JWT (`crear_token_acceso`) y validar contraseñas (`verificar_password`, `obtener_password_hash`).
* **`app/deps.py`**: Proveedores de dependencias FastAPI mediante `Depends()`:
  * `obtener_db()`: Sesión / base de datos activa de PyMongo.
  * `obtener_usuario_actual()`: Valida header `Authorization: Bearer <token>` y extrae usuario.
  * `requerir_rol(...)`: Middleware para control de acceso por roles.
* **`main.py`**: Inicializa `app = FastAPI()`, monta lifespan para conectar/desconectar PyMongo y registra los routers de cada módulo.

---

## 4. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Para profundizar en la organización de módulos y separación de capas:
* [`BuenasPracticasenPython/03_modularidad_archivos_entidades.md`](BuenasPracticasenPython/03_modularidad_archivos_entidades.md): Regla de una entidad por archivo para evitar archivos monolíticos (ej. subpaquete `entidades/incidente.py`, `entidades/solicitud.py`).
* [`BuenasPracticasenPython/11_arquitectura_en_capas_api.md`](BuenasPracticasenPython/11_arquitectura_en_capas_api.md): Flujo estricto de desacoplamiento entre Dominio, DTOs (Pydantic), Casos de Uso y Routers FastAPI.

---

`[⬅️ Anterior: 03_ARQUITECTURA_Y_PATRONES.md](03_ARQUITECTURA_Y_PATRONES.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 05_CLIENTE_DESCRITORIO_PYQT6.md](05_CLIENTE_DESCRITORIO_PYQT6.md)`
