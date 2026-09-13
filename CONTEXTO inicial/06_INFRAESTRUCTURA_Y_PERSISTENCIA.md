# 🗄️ 06 — Infraestructura, Persistencia y Despliegue

`[⬅️ Anterior: 05_CLIENTE_DESCRITORIO_PYQT6.md](05_CLIENTE_DESCRITORIO_PYQT6.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 07_TESTING_CALIDAD_Y_CONVENCIONES.md](07_TESTING_CALIDAD_Y_CONVENCIONES.md)`

---

## 1. Conexión a MongoDB (PyMongo)

La capa de infraestructura (`app/infraestructura/`) se comunica con MongoDB a través del driver oficial `pymongo` sin ORMs intermediarios.

* **Punto de conexión (`database.py`)**:
  Expone un cliente `MongoClient` administrado durante el ciclo de vida (*lifespan*) de FastAPI:
  ```python
  # Inicialización al arrancar FastAPI
  cliente = MongoClient(settings.MONGODB_URL)
  db = cliente[settings.MONGODB_DB_NAME]
  ```
* **Mapeo explícito de entidades**: Los repositorios concretos (`repo_usuarios.py`, `repo_requerimientos.py`) convierten documentos BSON a instancias puras de dominio y viceversa, manteniendo el dominio 100% agnóstico a MongoDB.

---

## 2. Colecciones e Índices

| Colección | Documento Clave | Índices Críticos |
|---|---|---|
| `usuarios` | Perfil, rol, password hash, `servicios_suscriptos`, `fecha_creacion`/`ultimo_acceso` | `email` (único) |
| `requerimientos` | Incidentes y solicitudes serializados, con `historial` y `comentarios` embebidos (ver abajo) | `_id` (único), `solicitante_id`, `estado`, `tipo` |
| `supervisiones` | Relación N:M `supervisor_id`/`supervisado_id` | `supervisor_id`, `supervisado_id` |
| `notificaciones` | `supervisor_id`, `empleado_supervisado_id`, `requerimiento_id`, `tipo_evento`, `detalle`, `leida` | `supervisor_id` |

> **No existe una colección `eventos` separada**: el historial de auditoría (`EventoRequerimiento`) y los comentarios (`Comentario`) se embeben como subdocumentos dentro del propio documento de `requerimientos` — no hay ningún caso de uso que necesite leerlos de forma independiente de su ticket (ver docstring de `repo_requerimientos.py`).

---

## 3. Variables de Entorno (`.env`)

El archivo `.env` se define en la raíz del proyecto (basado en `.env.example`):

```env
SECRET_KEY=clave-secreta-de-prueba-minimo-32-caracteres
ALGORITHM=HS256
EXPIRACION_MINUTOS=60
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=mesa_de_ayuda
```

> **En Docker**: `MONGODB_URL` apunta al servicio interno `mongodb://mongo:27017`.

---

## 4. Despliegue con Docker y Docker Compose

El archivo `docker-compose.yml` orquesta dos servicios vinculados en una red común:

```yaml
services:
  mongo:
    image: mongo:7
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  api:
    build: .
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - MONGODB_URL=mongodb://mongo:27017
      - MONGODB_DB_NAME=mesa_de_ayuda
      - SECRET_KEY=clave-de-prueba-local-12345
    depends_on:
      - mongo

volumes:
  mongo_data:
```

### Comandos de Operación:
```bash
# Levantar todo en segundo plano
docker compose up -d --build

# Ver logs del servicio API
docker compose logs -f api

# Detener los servicios
docker compose down
```

---

## 5. 📖 Ejemplos y Referencias Técnicas (Buenas Prácticas)

Para dominar la persistencia documental y el almacenamiento polimórfico:
* [`BuenasPracticasenPython/12_patron_repository_y_persistencia.md`](BuenasPracticasenPython/12_patron_repository_y_persistencia.md): Implementación paso a paso del repositorio abstracto y su adaptador PyMongo con operaciones CRUD puras.
* [`BuenasPracticasenPython/13_serializacion_polimorfica.md`](BuenasPracticasenPython/13_serializacion_polimorfica.md): Estrategia canónica para serializar y deserializar jerarquías `Incidente`/`Solicitud` desde documentos BSON usando el campo discriminador `tipo`.

---

`[⬅️ Anterior: 05_CLIENTE_DESCRITORIO_PYQT6.md](05_CLIENTE_DESCRITORIO_PYQT6.md)` | `[📑 Índice](00_INDICE_Y_GUIA_DE_LECTURA.md)` | `[Siguiente ➡️: 07_TESTING_CALIDAD_Y_CONVENCIONES.md](07_TESTING_CALIDAD_Y_CONVENCIONES.md)`
