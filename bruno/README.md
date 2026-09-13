# Colección Bruno — Mesa de Ayuda

Requiere:

1. El backend corriendo (`docker compose up -d`, o `uv run uvicorn app.main:app` local).
2. La base poblada con `uv run python -m scripts.seed_mongo` (la colección usa
   los usuarios sembrados: `sofia.jefa@...` supervisor, `rosa.molina@...`
   operador, `ivan.rios@...` técnico, `lucia.gomez@...` solicitante — todos
   con contraseña `Seed1234!`).

Correr toda la colección con el entorno `local`:

```bash
npx @usebruno/cli run bruno --env local
```

O abrirla en la app de escritorio de Bruno (`bruno/` como carpeta de colección).

Las carpetas están numeradas y cada request depende de las anteriores
(tokens e ids se pasan entre requests vía variables de entorno de Bruno):

- `01-usuarios/`: login de los 4 roles, alta/baja/cambio de rol de un
  usuario (solo Supervisor, incluye `servicios_suscriptos` al crear un
  Solicitante), un chequeo negativo (403 para un rol sin permiso), un
  segundo login de Solicitante y los perfiles de Operador/Técnico (para
  capturar sus ids, usados en `02-requerimientos/` y `03-supervision/`).
- `02-requerimientos/`: crear Incidente (`urgencia`/`categoria`/`servicio`/
  `pasos_reproduccion`) y Solicitud (`categoria`/`servicio`), listar con
  visibilidad propia, el flujo completo de transiciones de un Incidente
  (iniciar análisis → asignar técnico → iniciar progreso → resolver →
  cerrar), un chequeo negativo (409 al reintentar una transición sobre un
  requerimiento ya cerrado), y el fix de seguridad de `GET /{id}` (401 sin
  token, 403 si es de otro Solicitante).
- `03-supervision/`: un Supervisor asigna a un Operador como supervisado
  (409 si se repite, 403 si lo intenta alguien sin rol Supervisor), lista
  sus supervisados, y el Operador comenta un incidente nuevo (el anterior
  ya quedó `CERRADO` y no admite comentarios) para disparar una
  notificación real a su Supervisor.
- `04-notificaciones/`: el Supervisor lista sus notificaciones (incluye la
  generada por `03-supervision/06`) y la marca leída; un tercero sin rol
  Supervisor no puede tocarla (403).

> **Nota**: tanto el CLI (`bru.setEnvVar`) como la app de escritorio de
> Bruno persisten los valores seteados en tiempo de ejecución (tokens,
> ids) de vuelta en `environments/local.bru`. Si después de correr la
> colección ese archivo aparece con tokens/ids en vez de solo los 6 vars
> originales, es esperable — no versionar esos valores (`git checkout --
> bruno/environments/local.bru` antes de commitear).
