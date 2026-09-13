"""Tests de integración de la capa de infraestructura (Paso 5).

Usa `mongomock` en vez de un servidor MongoDB real: mismo protocolo que
PyMongo, sin depender de red ni de un contenedor Docker levantado. Valida
que los repositorios concretos cumplen el mismo contrato ABC que ya
prueban los `Fake*` de `tests/fakes.py`, pero con el mapeo real a/desde
documentos BSON.
"""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import mongomock
import pytest
from pymongo.database import Database

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.infraestructura.repo_requerimientos import RepositorioRequerimientosMongo
from app.infraestructura.repo_usuarios import RepositorioUsuariosMongo
from app.requerimientos.dominio.estados import EstadoRequerimiento
from app.requerimientos.dominio.incidente import Incidente, Severidad
from app.requerimientos.dominio.solicitud import CategoriaSolicitud, Solicitud
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.usuarios.dominio import Usuario


def _a_milisegundos(momento: datetime) -> datetime:
    """BSON solo guarda milisegundos: trunca para comparar contra el valor leído."""
    return momento.replace(microsecond=(momento.microsecond // 1000) * 1000)


@pytest.fixture
def db() -> Iterator[Database[dict[str, Any]]]:
    # tz_aware=True replica la configuración real de `crear_cliente_mongo`:
    # el dominio siempre trabaja con datetime aware (UTC).
    cliente: mongomock.MongoClient[dict[str, Any]] = mongomock.MongoClient(tz_aware=True)
    yield cliente["mesa_de_ayuda_test"]
    cliente.close()


@pytest.fixture
def repo_usuarios(db: Database[dict[str, Any]]) -> RepositorioUsuariosMongo:
    return RepositorioUsuariosMongo(db)


@pytest.fixture
def repo_requerimientos(db: Database[dict[str, Any]]) -> RepositorioRequerimientosMongo:
    return RepositorioRequerimientosMongo(db)


@pytest.fixture
def usuario() -> Usuario:
    return Usuario(
        nombre_completo="Ana Pérez",
        email="ana.perez@comunicarlos.com.ar",
        password_hash="hash-bcrypt-de-prueba",
        rol=RolUsuario.OPERADOR,
    )


class TestRepositorioUsuariosMongoGuardarYBuscar:
    def test_guardar_y_buscar_por_id_devuelve_el_mismo_usuario(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Act
        repo_usuarios.guardar(usuario)
        encontrado = repo_usuarios.buscar_por_id(usuario.id)

        # Assert
        assert encontrado is not None
        assert encontrado.id == usuario.id
        assert encontrado.nombre_completo == usuario.nombre_completo
        assert encontrado.email == usuario.email
        assert encontrado.password_hash == usuario.password_hash
        assert encontrado.rol == usuario.rol
        assert encontrado.activo == usuario.activo
        assert encontrado.fecha_creacion == _a_milisegundos(usuario.fecha_creacion)
        assert encontrado.ultimo_acceso == usuario.ultimo_acceso

    def test_guardar_y_buscar_conserva_servicios_suscriptos_y_ultimo_acceso(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Arrange
        solicitante = Usuario(
            nombre_completo="Sol",
            email="sol@gmail.com",
            password_hash="hash",
            rol=RolUsuario.SOLICITANTE,
            servicios_suscriptos=frozenset(
                {ServicioComunicarlos.TELEFONIA_CELULAR, ServicioComunicarlos.TELEVISION}
            ),
        )
        solicitante.registrar_acceso()

        # Act
        repo_usuarios.guardar(solicitante)
        encontrado = repo_usuarios.buscar_por_id(solicitante.id)

        # Assert
        assert encontrado is not None
        assert encontrado.servicios_suscriptos == solicitante.servicios_suscriptos
        assert solicitante.ultimo_acceso is not None
        assert encontrado.ultimo_acceso == _a_milisegundos(solicitante.ultimo_acceso)

    def test_buscar_por_id_inexistente_devuelve_none(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Act & Assert
        assert repo_usuarios.buscar_por_id(uuid.uuid4()) is None

    def test_buscar_por_email_encuentra_al_usuario(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Arrange
        repo_usuarios.guardar(usuario)

        # Act
        encontrado = repo_usuarios.buscar_por_email(usuario.email)

        # Assert
        assert encontrado is not None
        assert encontrado.id == usuario.id

    def test_buscar_por_email_inexistente_devuelve_none(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Act & Assert
        assert repo_usuarios.buscar_por_email("no-existe@comunicarlos.com") is None

    def test_guardar_es_upsert_no_duplica_documentos(
        self, repo_usuarios: RepositorioUsuariosMongo, usuario: Usuario
    ) -> None:
        # Arrange
        repo_usuarios.guardar(usuario)

        # Act: se reactiva y se guarda de nuevo el MISMO id
        usuario.desactivar()
        repo_usuarios.guardar(usuario)

        # Assert: sigue habiendo un solo documento, con el cambio reflejado
        assert len(repo_usuarios.listar_todos()) == 1
        encontrado = repo_usuarios.buscar_por_id(usuario.id)
        assert encontrado is not None
        assert encontrado.activo is False

    def test_listar_todos_devuelve_todos_los_usuarios_guardados(
        self, repo_usuarios: RepositorioUsuariosMongo
    ) -> None:
        # Arrange
        usuario_a = Usuario(
            nombre_completo="A",
            email="a@comunicarlos.com",
            password_hash="hash-a",
            rol=RolUsuario.SOLICITANTE,
            servicios_suscriptos=frozenset({ServicioComunicarlos.TELEVISION}),
        )
        usuario_b = Usuario(
            nombre_completo="B",
            email="b@comunicarlos.com.ar",
            password_hash="hash-b",
            rol=RolUsuario.TECNICO,
        )
        repo_usuarios.guardar(usuario_a)
        repo_usuarios.guardar(usuario_b)

        # Act
        todos = repo_usuarios.listar_todos()

        # Assert
        assert {u.id for u in todos} == {usuario_a.id, usuario_b.id}


@pytest.fixture
def solicitante_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def incidente(solicitante_id: uuid.UUID) -> Incidente:
    return Incidente(
        titulo="Corte de fibra troncal",
        descripcion="Sin conectividad en el barrio Centro.",
        solicitante_id=solicitante_id,
        severidad=Severidad.CRITICA,
        pasos_reproduccion="Verificar ONT sin luz de señal.",
        servicio_afectado="Fibra óptica residencial",
    )


class TestRepositorioRequerimientosMongoGuardarYBuscar:
    def test_guardar_y_buscar_incidente_devuelve_el_mismo_incidente(
        self, repo_requerimientos: RepositorioRequerimientosMongo, incidente: Incidente
    ) -> None:
        # Act
        repo_requerimientos.guardar(incidente)
        encontrado = repo_requerimientos.buscar_por_id(incidente.id)

        # Assert: tipo concreto e invariantes restauradas, no un evento
        # CREACION nuevo (el historial sigue teniendo exactamente 1 evento)
        assert isinstance(encontrado, Incidente)
        assert encontrado.id == incidente.id
        assert encontrado.titulo == incidente.titulo
        assert encontrado.estado == EstadoRequerimiento.ABIERTO
        assert encontrado.severidad == Severidad.CRITICA
        assert encontrado.pasos_reproduccion == incidente.pasos_reproduccion
        assert encontrado.servicio_afectado == incidente.servicio_afectado
        assert len(encontrado.historial) == 1
        assert encontrado.historial[0].id == incidente.historial[0].id
        assert encontrado.historial[0].tipo_evento == TipoEventoRequerimiento.CREACION

    def test_guardar_y_buscar_solicitud_devuelve_la_misma_solicitud(
        self, repo_requerimientos: RepositorioRequerimientosMongo, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        fecha_limite = datetime.now(UTC) + timedelta(days=5)
        solicitud = Solicitud(
            titulo="Alta de nuevo abono",
            descripcion="Cliente solicita nueva conexión.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.NUEVO_SERVICIO,
            fecha_limite=fecha_limite,
            impacto_estimado="Bajo",
        )

        # Act
        repo_requerimientos.guardar(solicitud)
        encontrada = repo_requerimientos.buscar_por_id(solicitud.id)

        # Assert
        assert isinstance(encontrada, Solicitud)
        assert encontrada.categoria == CategoriaSolicitud.NUEVO_SERVICIO
        assert encontrada.impacto_estimado == "Bajo"

    def test_buscar_por_id_inexistente_devuelve_none(
        self, repo_requerimientos: RepositorioRequerimientosMongo
    ) -> None:
        # Act & Assert
        assert repo_requerimientos.buscar_por_id(uuid.uuid4()) is None

    def test_guardar_tras_transiciones_restaura_estado_y_no_duplica_historial(
        self,
        repo_requerimientos: RepositorioRequerimientosMongo,
        incidente: Incidente,
    ) -> None:
        # Arrange: se avanza el incidente hasta EN_PROGRESO y se persiste en
        # cada paso, tal como haría ServicioRequerimientos._aplicar_transicion
        tecnico_id = uuid.uuid4()
        repo_requerimientos.guardar(incidente)
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        repo_requerimientos.guardar(incidente)
        incidente.asignar_tecnico(
            tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
        )
        repo_requerimientos.guardar(incidente)
        incidente.iniciar_progreso(autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)
        repo_requerimientos.guardar(incidente)

        # Act
        encontrado = repo_requerimientos.buscar_por_id(incidente.id)

        # Assert: un solo documento (upsert), estado y técnico restaurados,
        # y el historial completo de las 4 transiciones (sin duplicar ni
        # perder eventos por sucesivos guardar())
        assert len(repo_requerimientos.listar_todos()) == 1
        assert encontrado is not None
        assert encontrado.estado == EstadoRequerimiento.EN_PROGRESO
        assert encontrado.tecnico_asignado_id == tecnico_id
        assert len(encontrado.historial) == 4  # creación + 3 transiciones

        # Act: sigue siendo un objeto de dominio operable (no un DTO muerto);
        # se resuelve, se persiste el cambio y se vuelve a leer
        encontrado.resolver(
            "Se reemplazó el ONT.", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
        )
        repo_requerimientos.guardar(encontrado)
        resuelto = repo_requerimientos.buscar_por_id(incidente.id)

        # Assert
        assert resuelto is not None
        assert resuelto.estado == EstadoRequerimiento.RESUELTO

    def test_listar_todos_devuelve_incidentes_y_solicitudes_mezclados(
        self,
        repo_requerimientos: RepositorioRequerimientosMongo,
        incidente: Incidente,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Arrange
        solicitud = Solicitud(
            titulo="Cambio de abono",
            descripcion="Upgrade a plan superior.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.CAMBIO_ABONO,
            fecha_limite=datetime.now(UTC) + timedelta(days=2),
            impacto_estimado="Medio",
        )
        repo_requerimientos.guardar(incidente)
        repo_requerimientos.guardar(solicitud)

        # Act
        todos = repo_requerimientos.listar_todos()

        # Assert
        assert {type(r) for r in todos} == {Incidente, Solicitud}
        assert {r.id for r in todos} == {incidente.id, solicitud.id}

    def test_listar_por_solicitante_filtra_correctamente(
        self,
        repo_requerimientos: RepositorioRequerimientosMongo,
        incidente: Incidente,
    ) -> None:
        # Arrange
        otro_solicitante_id = uuid.uuid4()
        otro_incidente = Incidente(
            titulo="Otro corte",
            descripcion="Otro barrio.",
            solicitante_id=otro_solicitante_id,
            severidad=Severidad.BAJA,
            pasos_reproduccion="p",
            servicio_afectado="TV",
        )
        repo_requerimientos.guardar(incidente)
        repo_requerimientos.guardar(otro_incidente)

        # Act
        propios = repo_requerimientos.listar_por_solicitante(incidente.solicitante_id)

        # Assert
        assert {r.id for r in propios} == {incidente.id}

    def test_reconstruye_sin_disparar_un_evento_creacion_nuevo(
        self, repo_requerimientos: RepositorioRequerimientosMongo, incidente: Incidente
    ) -> None:
        # Arrange: guardar y volver a leer varias veces no debe ir
        # acumulando eventos CREACION (regresión del bug que motivó
        # `Incidente.reconstruir`)
        repo_requerimientos.guardar(incidente)
        repo_requerimientos.buscar_por_id(incidente.id)
        repo_requerimientos.buscar_por_id(incidente.id)

        # Act
        encontrado = repo_requerimientos.buscar_por_id(incidente.id)

        # Assert
        assert encontrado is not None
        eventos_creacion = [
            e for e in encontrado.historial if e.tipo_evento == TipoEventoRequerimiento.CREACION
        ]
        assert len(eventos_creacion) == 1

    def test_evento_reconstruido_preserva_autor_y_detalle_originales(
        self, repo_requerimientos: RepositorioRequerimientosMongo, incidente: Incidente
    ) -> None:
        # Arrange
        evento_original = incidente.historial[0]

        # Act
        repo_requerimientos.guardar(incidente)
        encontrado = repo_requerimientos.buscar_por_id(incidente.id)

        # Assert
        assert encontrado is not None
        evento_reconstruido = encontrado.historial[0]
        assert evento_reconstruido.autor_id == evento_original.autor_id
        assert evento_reconstruido.detalle == evento_original.detalle
        assert isinstance(evento_reconstruido, EventoRequerimiento)
