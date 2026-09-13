"""Tests de servicios del módulo `app/requerimientos/`.

Verifica la integración real entre `FakeRepositorioRequerimientos`,
`FabricaRequerimientos`, la entidad `Requerimiento` y `DespachadorEventos`.
"""

import uuid

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.observador import ObservadorRequerimiento
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.incidente import CategoriaIncidente, UrgenciaIncidente
from app.requerimientos.dominio.solicitud import CategoriaSolicitud
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import PermisoDenegadoError, RequerimientoNoEncontradoError
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
        urgencia=UrgenciaIncidente.IMPORTANTE,
        categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
        servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        pasos_reproduccion="Reiniciar ONT.",
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
        requerimiento = servicio.crear(
            TipoRequerimiento.SOLICITUD,
            titulo="Alta de servicio",
            descripcion="Nueva conexión residencial.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.ALTA_SERVICIO,
            servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
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


class TestObtenerVisiblePara:
    def test_solicitante_puede_ver_su_propio_requerimiento(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        propio = _crear_incidente(servicio, solicitante_id)

        # Act
        encontrado = servicio.obtener_visible_para(
            propio.id, RolUsuario.SOLICITANTE, solicitante_id
        )

        # Assert
        assert encontrado.id == propio.id

    def test_solicitante_no_puede_ver_un_requerimiento_ajeno(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        ajeno = _crear_incidente(servicio, uuid.uuid4())

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            servicio.obtener_visible_para(ajeno.id, RolUsuario.SOLICITANTE, solicitante_id)

    def test_operador_puede_ver_cualquier_requerimiento(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        ajeno = _crear_incidente(servicio, uuid.uuid4())

        # Act
        encontrado = servicio.obtener_visible_para(ajeno.id, RolUsuario.OPERADOR, solicitante_id)

        # Assert
        assert encontrado.id == ajeno.id

    def test_id_inexistente_lanza_requerimiento_no_encontrado(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Act & Assert
        with pytest.raises(RequerimientoNoEncontradoError):
            servicio.obtener_visible_para(uuid.uuid4(), RolUsuario.OPERADOR, solicitante_id)


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


class TestComentariosYDerivacionViaServicio:
    def test_agregar_comentario_persiste_y_notifica_un_evento(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)

        # Act
        comentario = servicio.agregar_comentario(
            requerimiento.id, "¿Alguna novedad?", solicitante_id, RolUsuario.SOLICITANTE
        )

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.comentarios == [comentario]
        assert len(espia.eventos_recibidos) == 2  # creación + comentario

    def test_agregar_comentario_que_reabre_notifica_los_dos_eventos_nuevos(
        self,
        servicio: ServicioRequerimientos,
        solicitante_id: uuid.UUID,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange: lleva el incidente hasta RESUELTO
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_id = uuid.uuid4()
        servicio.iniciar_analisis(requerimiento.id, uuid.uuid4(), RolUsuario.OPERADOR)
        servicio.asignar_tecnico(requerimiento.id, tecnico_id, uuid.uuid4(), RolUsuario.OPERADOR)
        servicio.iniciar_progreso(requerimiento.id, tecnico_id, RolUsuario.TECNICO)
        servicio.resolver(requerimiento.id, "Nota.", tecnico_id, RolUsuario.TECNICO)
        cantidad_previa = len(espia.eventos_recibidos)

        # Act
        servicio.agregar_comentario(
            requerimiento.id, "No quedó resuelto.", uuid.uuid4(), RolUsuario.OPERADOR
        )

        # Assert: se despacharon COMENTARIO y REAPERTURA, no solo el último
        eventos_nuevos = espia.eventos_recibidos[cantidad_previa:]
        assert [e.tipo_evento for e in eventos_nuevos] == [
            TipoEventoRequerimiento.COMENTARIO,
            TipoEventoRequerimiento.REAPERTURA,
        ]

    def test_derivar_interconsulta_reasigna_y_persiste(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_origen_id = uuid.uuid4()
        tecnico_destino_id = uuid.uuid4()
        servicio.iniciar_analisis(requerimiento.id, uuid.uuid4(), RolUsuario.OPERADOR)
        servicio.asignar_tecnico(
            requerimiento.id, tecnico_origen_id, uuid.uuid4(), RolUsuario.OPERADOR
        )

        # Act
        servicio.derivar_interconsulta(
            requerimiento.id, tecnico_destino_id, tecnico_origen_id, RolUsuario.TECNICO
        )

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id == tecnico_destino_id
