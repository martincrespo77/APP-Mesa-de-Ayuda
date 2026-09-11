# 🖥️ 05 — Cliente de Escritorio (PyQt6)

`[⬅️ Anterior: 04_MODULOS_Y_ESTRUCTURA_CODIGO.md](04_MODULOS_Y_ESTRUCTURA_CODIGO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 06_INFRAESTRUCTURA_Y_PERSISTENCIA.md](06_INFRAESTRUCTURA_Y_PERSISTENCIA.md)`

---

## 1. Arquitectura del Frontend de Escritorio

El cliente de escritorio reside en `desktop/` y es **completamente independiente** del backend. No importa clases ni modelos de `app/`. Toda la comunicación ocurre vía HTTP estándar mediante `httpx`.

```
desktop/
├── api_client.py           # Adaptador de comunicación HTTP con la API
├── styles.py               # Tema visual global oscuro (QSS)
├── main.py                 # Punto de entrada y gestión de ciclo de vida Qt
└── views/
    ├── login_window.py     # Ventana de autenticación
    └── main_window.py      # Ventana principal (Dashboard + Pestañas)
```

---

## 2. ApiClient y Modo Demostración Offline

El componente `ApiClient` (`desktop/api_client.py`) implementa la comunicación con FastAPI:
* **Manejo de Sesión**: Almacena el token JWT en memoria y lo inyecta automáticamente en los headers (`Authorization: Bearer <token>`).
* **Decodificación de Claims**: Extrae el rol y el ID de usuario del payload JWT sin requerir la clave secreta en el cliente.
* **Modo Demostración (`--demo`)**: Si se activa mediante el flag de CLI o el checkbox en la pantalla de login, el cliente intercepta las operaciones y devuelve datasets sintéticos predefinidos. Esto permite evaluar y presentar la interfaz sin necesidad de tener Docker, MongoDB ni FastAPI en ejecución.

---

## 3. Vistas y Componentes Principales

### A. Ventana de Login (`LoginWindow`)
* Campos de correo electrónico y contraseña.
* Checkbox interactivo para alternar "Modo Demostración".
* Verificación previa de conectividad contra el endpoint `/health` de la API.
* Detección automática del rol según las credenciales suministradas.

### B. Ventana Principal (`MainWindow`)
Organizada en tres pestañas accesibles mediante navegación superior:
1. **Requerimientos**:
   * Barra de búsqueda por texto libre (título o ID).
   * Filtros combinados por Estado y Tipo/Severidad.
   * `QTableWidget` con listado de tickets formateados.
   * Panel lateral de detalle con información completa, historial de eventos y botón para cambiar de estado.
2. **Nuevo Requerimiento**:
   * Formulario reactivo: al cambiar el tipo entre *Incidente* y *Solicitud*, los campos específicos (severidad, pasos de reproducción, impacto) se muestran o se ocultan dinámicamente.
3. **Notificaciones**:
   * Panel de alertas del sistema e historial de eventos emitidos por el despachador.

---

## 4. Estilos y Experiencia Visual (`styles.py`)

La apariencia se define mediante una hoja de estilos global QSS inyectada en `QApplication`:
* Paleta oscura profesional (fondos `#1e1e2e`, tarjetas `#252538`, acentos violeta `#7c3aed` y azul `#3b82f6`).
* Badges de colores semánticos para estados: Verde (Resuelto/Cerrado), Naranja (En progreso), Rojo (Alta/Crítica).

---

## 5. Comando de Ejecución

```bash
# Modo demo offline (inmediato, sin backend)
uv run python -m desktop.main --demo

# Modo conectado (requiere API corriendo en localhost:8000)
uv run python -m desktop.main
```

---

`[⬅️ Anterior: 04_MODULOS_Y_ESTRUCTURA_CODIGO.md](04_MODULOS_Y_ESTRUCTURA_CODIGO.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 06_INFRAESTRUCTURA_Y_PERSISTENCIA.md](06_INFRAESTRUCTURA_Y_PERSISTENCIA.md)`
