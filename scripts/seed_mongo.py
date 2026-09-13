"""Script de seed: puebla una MongoDB real con datos de ejemplo (Paso 5).

Uso:
    uv run python -m scripts.seed_mongo

Requiere las variables de entorno configuradas (ver `.env.example`) y un
servidor MongoDB accesible en `MONGODB_URL`. Pensado para:
1. Verificar visualmente los datos en MongoDB (`mongosh`, Compass).
2. Probar el cliente de escritorio PyQt6 (Paso 6) contra un backend con
   datos reales, sin depender solo del Modo Demo offline.

Usa las entidades de dominio y los repositorios concretos de PyMongo
directamente (no pasa por los servicios de aplicación ni por la API
HTTP). Los ids son deterministas (UUID5 a partir de una clave legible),
así que correr el script varias veces reemplaza los mismos documentos
(upsert) en vez de duplicarlos.
"""

import uuid
from datetime import UTC, datetime, timedelta

from app.auth import obtener_password_hash
from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.config import get_settings
from app.infraestructura.database import crear_cliente_mongo, crear_indices, obtener_base_datos
from app.infraestructura.repo_requerimientos import RepositorioRequerimientosMongo
from app.infraestructura.repo_usuarios import RepositorioUsuariosMongo
from app.requerimientos.dominio.incidente import Incidente, Severidad
from app.requerimientos.dominio.solicitud import CategoriaSolicitud, Solicitud
from app.usuarios.dominio import Usuario

_NAMESPACE_SEED = uuid.uuid5(uuid.NAMESPACE_DNS, "mesa-de-ayuda-comunicarlos.seed")
_PASSWORD_SEED = "Seed1234!"


def _id(clave: str) -> uuid.UUID:
    """UUID estable a partir de una clave legible: reproducible entre corridas."""
    return uuid.uuid5(_NAMESPACE_SEED, clave)


def _crear_usuarios() -> dict[str, Usuario]:
    """Un usuario por cada uno de los 4 roles, más un segundo solicitante."""
    password_hash = obtener_password_hash(_PASSWORD_SEED)
    datos: tuple[tuple[str, str, str, RolUsuario, frozenset[ServicioComunicarlos]], ...] = (
        (
            "solicitante1",
            "Lucía Gómez",
            "lucia.gomez@comunicarlos.com",
            RolUsuario.SOLICITANTE,
            frozenset({ServicioComunicarlos.INTERNET_BANDA_ANCHA, ServicioComunicarlos.TELEVISION}),
        ),
        (
            "solicitante2",
            "Marcos Díaz",
            "marcos.diaz@comunicarlos.com",
            RolUsuario.SOLICITANTE,
            frozenset({ServicioComunicarlos.TELEFONIA_CELULAR}),
        ),
        (
            "operador1",
            "Rosa Molina",
            "rosa.molina@comunicarlos.com.ar",
            RolUsuario.OPERADOR,
            frozenset(),
        ),
        (
            "tecnico1",
            "Iván Ríos",
            "ivan.rios@comunicarlos.com.ar",
            RolUsuario.TECNICO,
            frozenset(),
        ),
        (
            "supervisor1",
            "Sofía Jefa",
            "sofia.jefa@comunicarlos.com.ar",
            RolUsuario.SUPERVISOR,
            frozenset(),
        ),
    )
    return {
        clave: Usuario(
            id=_id(clave),
            nombre_completo=nombre,
            email=email,
            password_hash=password_hash,
            rol=rol,
            servicios_suscriptos=servicios,
        )
        for clave, nombre, email, rol, servicios in datos
    }


def _crear_requerimientos(usuarios: dict[str, Usuario]) -> list[Incidente | Solicitud]:
    """Incidentes y solicitudes cubriendo los 6 estados del ciclo de vida."""
    solicitante1 = usuarios["solicitante1"].id
    solicitante2 = usuarios["solicitante2"].id
    operador_id = usuarios["operador1"].id
    tecnico_id = usuarios["tecnico1"].id
    operador = RolUsuario.OPERADOR
    tecnico = RolUsuario.TECNICO

    incidente_abierto = Incidente(
        id=_id("incidente-abierto"),
        titulo="Corte total de fibra en Barrio Centro",
        descripcion="Sin conectividad desde esta mañana.",
        solicitante_id=solicitante1,
        severidad=Severidad.CRITICA,
        pasos_reproduccion="ONT sin luz de señal.",
        servicio_afectado="Fibra óptica residencial",
    )

    incidente_en_analisis = Incidente(
        id=_id("incidente-en-analisis"),
        titulo="Intermitencia en telefonía IP",
        descripcion="Cortes de llamada cada pocos minutos.",
        solicitante_id=solicitante2,
        severidad=Severidad.MEDIA,
        pasos_reproduccion="Llamar y esperar 5 minutos.",
        servicio_afectado="Telefonía IP",
    )
    incidente_en_analisis.iniciar_analisis(autor_id=operador_id, rol_actor=operador)

    incidente_en_progreso = Incidente(
        id=_id("incidente-en-progreso"),
        titulo="Degradación de señal de TV",
        descripcion="Pixelado constante en varios canales.",
        solicitante_id=solicitante1,
        severidad=Severidad.ALTA,
        pasos_reproduccion="Sintonizar cualquier canal HD.",
        servicio_afectado="TV por fibra",
    )
    incidente_en_progreso.iniciar_analisis(autor_id=operador_id, rol_actor=operador)
    incidente_en_progreso.asignar_tecnico(tecnico_id, autor_id=operador_id, rol_actor=operador)
    incidente_en_progreso.iniciar_progreso(autor_id=tecnico_id, rol_actor=tecnico)

    incidente_resuelto = Incidente(
        id=_id("incidente-resuelto"),
        titulo="Router no enciende",
        descripcion="El equipo dejó de responder tras un corte de luz.",
        solicitante_id=solicitante2,
        severidad=Severidad.BAJA,
        pasos_reproduccion="Verificar led de encendido.",
        servicio_afectado="Fibra óptica residencial",
    )
    incidente_resuelto.iniciar_analisis(autor_id=operador_id, rol_actor=operador)
    incidente_resuelto.asignar_tecnico(tecnico_id, autor_id=operador_id, rol_actor=operador)
    incidente_resuelto.iniciar_progreso(autor_id=tecnico_id, rol_actor=tecnico)
    incidente_resuelto.resolver(
        "Se reemplazó la fuente de alimentación del router.",
        autor_id=tecnico_id,
        rol_actor=tecnico,
    )

    incidente_cerrado = Incidente(
        id=_id("incidente-cerrado"),
        titulo="Sin señal de fibra en oficina",
        descripcion="Caída total del enlace corporativo.",
        solicitante_id=solicitante1,
        severidad=Severidad.ALTA,
        pasos_reproduccion="Revisar ONT y patchera.",
        servicio_afectado="Fibra óptica corporativa",
    )
    incidente_cerrado.iniciar_analisis(autor_id=operador_id, rol_actor=operador)
    incidente_cerrado.asignar_tecnico(tecnico_id, autor_id=operador_id, rol_actor=operador)
    incidente_cerrado.iniciar_progreso(autor_id=tecnico_id, rol_actor=tecnico)
    incidente_cerrado.resolver(
        "Se empalmó la fibra cortada.", autor_id=tecnico_id, rol_actor=tecnico
    )
    incidente_cerrado.cerrar(autor_id=solicitante1, rol_actor=RolUsuario.SOLICITANTE)

    incidente_cancelado = Incidente(
        id=_id("incidente-cancelado"),
        titulo="Lentitud reportada por error",
        descripcion="El cliente confirmó que era un problema local, no de red.",
        solicitante_id=solicitante2,
        severidad=Severidad.BAJA,
        pasos_reproduccion="N/A",
        servicio_afectado="Fibra óptica residencial",
    )
    incidente_cancelado.cancelar(autor_id=solicitante2, rol_actor=RolUsuario.SOLICITANTE)

    solicitud_abierta = Solicitud(
        id=_id("solicitud-abierta"),
        titulo="Alta de nuevo servicio de internet",
        descripcion="Cliente nuevo solicita instalación.",
        solicitante_id=solicitante1,
        categoria=CategoriaSolicitud.NUEVO_SERVICIO,
        fecha_limite=datetime.now(UTC) + timedelta(days=10),
        impacto_estimado="Bajo",
    )

    solicitud_en_progreso = Solicitud(
        id=_id("solicitud-en-progreso"),
        titulo="Upgrade de abono a plan superior",
        descripcion="Cliente pide más velocidad de bajada.",
        solicitante_id=solicitante2,
        categoria=CategoriaSolicitud.CAMBIO_ABONO,
        fecha_limite=datetime.now(UTC) + timedelta(days=3),
        impacto_estimado="Medio",
    )
    solicitud_en_progreso.iniciar_analisis(autor_id=operador_id, rol_actor=operador)
    solicitud_en_progreso.asignar_tecnico(tecnico_id, autor_id=operador_id, rol_actor=operador)
    solicitud_en_progreso.iniciar_progreso(autor_id=tecnico_id, rol_actor=tecnico)

    return [
        incidente_abierto,
        incidente_en_analisis,
        incidente_en_progreso,
        incidente_resuelto,
        incidente_cerrado,
        incidente_cancelado,
        solicitud_abierta,
        solicitud_en_progreso,
    ]


def main() -> None:
    settings = get_settings()
    cliente = crear_cliente_mongo(settings)
    db = obtener_base_datos(cliente, settings)
    crear_indices(db)

    repo_usuarios = RepositorioUsuariosMongo(db)
    repo_requerimientos = RepositorioRequerimientosMongo(db)

    usuarios = _crear_usuarios()
    for usuario in usuarios.values():
        repo_usuarios.guardar(usuario)
    print(f"Usuarios sembrados: {len(usuarios)} (contraseña: {_PASSWORD_SEED!r})")

    requerimientos = _crear_requerimientos(usuarios)
    for requerimiento in requerimientos:
        repo_requerimientos.guardar(requerimiento)
    print(f"Requerimientos sembrados: {len(requerimientos)}")

    cliente.close()


if __name__ == "__main__":
    main()
