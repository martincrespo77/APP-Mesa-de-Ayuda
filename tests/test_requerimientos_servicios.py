"""Tests de servicios del módulo `app/requerimientos/`.

Verifica la integración real entre `FakeRepositorioRequerimientos`,
`FabricaRequerimientos`, la entidad `Requerimiento` y `DespachadorEventos`.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.dominio import RolUsuario
from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.observador import ObservadorRequerimiento
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.incidente import Severidad
from app.requerimientos.eventos import EventoRequerimiento
from app.requerimientos.excepciones import RequerimientoNoEncontradoError
from app.requerimientos.servicios import ServicioRequerimientos
from tests.fakes import FakeRepositorioRequerimientos


class _ObservadorEspia(ObservadorRequerimiento):
    def __init__(self) -> None:
        self.eventos_recibidos: list[EventoRequerimiento] = []

    def actualizar(self, evento: EventoRequerimiento) -> None:
        self.eventos_recibidos.append(evento)


@pytest.fixture
def repositorio() -> FakeRepositorioRequerimientos:
    return FakeRepositorioRequerimientos()


@pytest.fixture
def espia() -> _ObservadorEspia:
    return _ObservadorEspia()


@pytest.fixture
def despachador(espia: _ObservadorEspia) -> DespachadorEventos:
    despachador = DespachadorEventos()
    despachador.suscribir(espia)
    return despachador


@pytest.fixture
def servicio(
    repositorio: FakeRepositorioRequerimientos, despachador: DespachadorEventos
) -> ServicioRequerimientos:
    return ServicioRequerimientos(repositorio, despachador)


@pytest.fixture
def solicitante_id() -> uuid.UUID:
    return uuid.uuid4()


def _crear_incidente(servicio: ServicioRequerimientos, solicitante_id: uuid.UUID):
    return servicio.crear(
        TipoRequerimiento.INCIDENTE,
        titulo="Corte de fibra",
        descripcion="Sin señal en el sector norte.",
        solicitante_id=solicitante_id,
        severidad=Severidad.ALTA,
        pasos_reproduccion="Reiniciar ONT.",
        servicio_afectado="Fibra óptica",
    )


class TestCrear:
    def test_crear_persiste_el_requerimiento_en_el_repositorio(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Act
        requerimiento = _crear_incidente(servicio, solicitante_id)

        # Assert
        assert repositorio.buscar_por_id(requerimiento.id) is requerimiento

    def test_crear_notifica_el_evento_de_creacion_al_despachador(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID, espia: _ObservadorEspia
    ) -> None:
        # Act
        _crear_incidente(servicio, solicitante_id)

        # Assert
        assert len(espia.eventos_recibidos) == 1
        assert espia.eventos_recibidos[0].tipo_evento.value == "CREACION"

    def test_crear_solicitud_via_fabrica(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Act
        from app.requerimientos.dominio.solicitud import CategoriaSolicitud

        requerimiento = servicio.crear(
            TipoRequerimiento.SOLICITUD,
            titulo="Alta de servicio",
            descripcion="Nueva conexión residencial.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.NUEVO_SERVICIO,
            fecha_limite=datetime.now(UTC) + timedelta(days=3),
            impacto_estimado="Bajo",
        )

        # Assert
        assert requerimiento.tipo == TipoRequerimiento.SOLICITUD


class TestConsultas:
    def test_obtener_por_id_inexistente_devuelve_none(
        self, servicio: ServicioRequerimientos
    ) -> None:
        # Act & Assert
        assert servicio.obtener_por_id(uuid.uuid4()) is None

    def test_solicitante_solo_ve_sus_propios_requerimientos(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        propio = _crear_incidente(servicio, solicitante_id)
        _crear_incidente(servicio, uuid.uuid4())  # de otro solicitante

        # Act
        visibles = servicio.listar_visibles_para(RolUsuario.SOLICITANTE, solicitante_id)

        # Assert
        assert [r.id for r in visibles] == [propio.id]

    def test_operador_ve_todos_los_requerimientos(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        _crear_incidente(servicio, solicitante_id)
        _crear_incidente(servicio, uuid.uuid4())

        # Act
        visibles = servicio.listar_visibles_para(RolUsuario.OPERADOR, solicitante_id)

        # Assert
        assert len(visibles) == 2


class TestTransicionesViaServicio:
    def test_iniciar_analisis_persiste_y_notifica(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)

        # Act
        servicio.iniciar_analisis(
            requerimiento.id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
        )

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.estado == EstadoRequerimiento.EN_ANALISIS
        assert len(espia.eventos_recibidos) == 2  # creación + cambio de estado

    def test_transicion_sobre_id_inexistente_lanza_requerimiento_no_encontrado(
        self, servicio: ServicioRequerimientos
    ) -> None:
        # Act & Assert
        with pytest.raises(RequerimientoNoEncontradoError):
            servicio.iniciar_analisis(
                uuid.uuid4(), autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
            )

    def test_flujo_completo_hasta_cierre_a_traves_del_servicio(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_id = uuid.uuid4()

        # Act
        servicio.iniciar_analisis(requerimiento.id, uuid.uuid4(), RolUsuario.OPERADOR)
        servicio.asignar_tecnico(requerimiento.id, tecnico_id, uuid.uuid4(), RolUsuario.OPERADOR)
        servicio.iniciar_progreso(requerimiento.id, tecnico_id, RolUsuario.TECNICO)
        servicio.resolver(requerimiento.id, "ONT reemplazado.", tecnico_id, RolUsuario.TECNICO)
        servicio.cerrar(requerimiento.id, solicitante_id, RolUsuario.SOLICITANTE)

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.estado == EstadoRequerimiento.CERRADO
        assert len(espia.eventos_recibidos) == 6  # creación + 5 transiciones
