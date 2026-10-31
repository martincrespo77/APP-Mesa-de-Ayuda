"""Tests de servicios del módulo `app/requerimientos/`.

Verifica la ORQUESTACIÓN entre `FakeRepositorioRequerimientos`,
`FabricaRequerimientos`, las entidades y `DespachadorEventos`: que el
servicio recupere lo necesario, delegue en el dominio, persista y notifique
cada evento, y que valide lo que solo él puede saber (que un id exista).

Las reglas de negocio (quién puede ver, asignar, derivar; a quién se le
puede asignar un ticket) NO se prueban acá: son responsabilidad de
`Requerimiento` y de cada rol de `Usuario`, y viven en
`test_requerimientos_dominio.py` y `test_usuarios_dominio.py`.
"""

import uuid

import pytest

from app.compartido.dominio import ServicioComunicarlos
from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.observador import ObservadorRequerimiento
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.incidente import CategoriaIncidente, UrgenciaIncidente
from app.requerimientos.dominio.solicitud import CategoriaSolicitud
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    PermisoDenegadoError,
    RequerimientoNoEncontradoError,
    TecnicoInvalidoError,
)
from app.requerimientos.servicios import ServicioRequerimientos
from app.usuarios.dominio import Operador, Solicitante, Tecnico
from tests.actores import un_operador, un_solicitante, un_tecnico
from tests.fakes import FakeRepositorioRequerimientos, FakeRepositorioUsuarios


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
def repo_usuarios() -> FakeRepositorioUsuarios:
    return FakeRepositorioUsuarios()


@pytest.fixture
def servicio(
    repositorio: FakeRepositorioRequerimientos,
    despachador: DespachadorEventos,
    repo_usuarios: FakeRepositorioUsuarios,
) -> ServicioRequerimientos:
    return ServicioRequerimientos(repositorio, despachador, repo_usuarios)


@pytest.fixture
def solicitante() -> Solicitante:
    return un_solicitante()


@pytest.fixture
def operador() -> Operador:
    return un_operador()


@pytest.fixture
def tecnico(repo_usuarios: FakeRepositorioUsuarios) -> Tecnico:
    """Técnico dado de alta en el repositorio (el servicio lo busca por id)."""
    tecnico = un_tecnico()
    repo_usuarios.guardar(tecnico)
    return tecnico


@pytest.fixture
def tecnico_destino(repo_usuarios: FakeRepositorioUsuarios) -> Tecnico:
    tecnico = un_tecnico(email="marta.suarez@comunicarlos.com.ar")
    repo_usuarios.guardar(tecnico)
    return tecnico


def _crear_incidente(
    servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
) -> Requerimiento:
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
        solicitante: Solicitante,
    ) -> None:
        # Act
        requerimiento = _crear_incidente(servicio, solicitante.id)

        # Assert
        assert repositorio.buscar_por_id(requerimiento.id) is requerimiento

    def test_crear_notifica_el_evento_de_creacion_al_despachador(
        self, servicio: ServicioRequerimientos, solicitante: Solicitante, espia: _ObservadorEspia
    ) -> None:
        # Act
        _crear_incidente(servicio, solicitante.id)

        # Assert
        assert len(espia.eventos_recibidos) == 1
        assert espia.eventos_recibidos[0].tipo_evento == TipoEventoRequerimiento.CREACION

    def test_crear_solicitud_via_fabrica(
        self, servicio: ServicioRequerimientos, solicitante: Solicitante
    ) -> None:
        # Act
        requerimiento = servicio.crear(
            TipoRequerimiento.SOLICITUD,
            titulo="Alta de servicio",
            descripcion="Nueva conexión residencial.",
            solicitante_id=solicitante.id,
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

    def test_listar_visibles_devuelve_lo_que_el_actor_dice_que_puede_ver(
        self, servicio: ServicioRequerimientos, solicitante: Solicitante, operador: Operador
    ) -> None:
        # Arrange
        propio = _crear_incidente(servicio, solicitante.id)
        _crear_incidente(servicio, uuid.uuid4())  # de otro solicitante

        # Act
        visibles_para_solicitante = servicio.listar_visibles_para(solicitante)
        visibles_para_operador = servicio.listar_visibles_para(operador)

        # Assert: el servicio no decide, filtra con `actor.puede_ver(...)`
        assert [r.id for r in visibles_para_solicitante] == [propio.id]
        assert len(visibles_para_operador) == 2

    def test_obtener_visible_devuelve_el_requerimiento(
        self, servicio: ServicioRequerimientos, solicitante: Solicitante
    ) -> None:
        # Arrange
        propio = _crear_incidente(servicio, solicitante.id)

        # Act
        encontrado = servicio.obtener_visible_para(propio.id, solicitante)

        # Assert
        assert encontrado.id == propio.id

    def test_obtener_visible_propaga_el_rechazo_del_dominio(
        self, servicio: ServicioRequerimientos, solicitante: Solicitante
    ) -> None:
        # Arrange
        ajeno = _crear_incidente(servicio, uuid.uuid4())

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            servicio.obtener_visible_para(ajeno.id, solicitante)

    def test_obtener_visible_con_id_inexistente_lanza_no_encontrado(
        self, servicio: ServicioRequerimientos, operador: Operador
    ) -> None:
        # Act & Assert
        with pytest.raises(RequerimientoNoEncontradoError):
            servicio.obtener_visible_para(uuid.uuid4(), operador)


class TestTransicionesViaServicio:
    def test_iniciar_analisis_persiste_y_notifica(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante: Solicitante,
        operador: Operador,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)

        # Act
        servicio.iniciar_analisis(requerimiento.id, operador)

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.estado == EstadoRequerimiento.EN_ANALISIS
        assert len(espia.eventos_recibidos) == 2  # creación + cambio de estado

    def test_transicion_sobre_id_inexistente_lanza_requerimiento_no_encontrado(
        self, servicio: ServicioRequerimientos, operador: Operador
    ) -> None:
        # Act & Assert
        with pytest.raises(RequerimientoNoEncontradoError):
            servicio.iniciar_analisis(uuid.uuid4(), operador)

    def test_transicion_rechazada_por_el_dominio_no_notifica(
        self,
        servicio: ServicioRequerimientos,
        solicitante: Solicitante,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)

        # Act: el error de dominio se propaga tal cual
        with pytest.raises(PermisoDenegadoError):
            servicio.iniciar_analisis(requerimiento.id, solicitante)

        # Assert: solo se notificó la creación
        assert len(espia.eventos_recibidos) == 1

    def test_flujo_completo_hasta_cierre_a_traves_del_servicio(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante: Solicitante,
        operador: Operador,
        espia: _ObservadorEspia,
        tecnico: Tecnico,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)

        # Act
        servicio.iniciar_analisis(requerimiento.id, operador)
        servicio.asignar_tecnico(requerimiento.id, tecnico.id, operador)
        servicio.iniciar_progreso(requerimiento.id, tecnico)
        servicio.resolver(requerimiento.id, "ONT reemplazado.", tecnico)
        servicio.cerrar(requerimiento.id, solicitante)

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
        solicitante: Solicitante,
        espia: _ObservadorEspia,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)

        # Act
        comentario = servicio.agregar_comentario(requerimiento.id, "¿Alguna novedad?", solicitante)

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.comentarios == [comentario]
        assert len(espia.eventos_recibidos) == 2  # creación + comentario

    def test_agregar_comentario_que_reabre_notifica_los_dos_eventos_nuevos(
        self,
        servicio: ServicioRequerimientos,
        solicitante: Solicitante,
        operador: Operador,
        espia: _ObservadorEspia,
        tecnico: Tecnico,
    ) -> None:
        # Arrange: lleva el incidente hasta RESUELTO
        requerimiento = _crear_incidente(servicio, solicitante.id)
        servicio.iniciar_analisis(requerimiento.id, operador)
        servicio.asignar_tecnico(requerimiento.id, tecnico.id, operador)
        servicio.iniciar_progreso(requerimiento.id, tecnico)
        servicio.resolver(requerimiento.id, "Nota.", tecnico)
        cantidad_previa = len(espia.eventos_recibidos)

        # Act
        servicio.agregar_comentario(requerimiento.id, "No quedó resuelto.", operador)

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
        solicitante: Solicitante,
        operador: Operador,
        tecnico: Tecnico,
        tecnico_destino: Tecnico,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)
        servicio.iniciar_analisis(requerimiento.id, operador)
        servicio.asignar_tecnico(requerimiento.id, tecnico.id, operador)

        # Act
        servicio.derivar_interconsulta(requerimiento.id, tecnico_destino.id, tecnico)

        # Assert
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id == tecnico_destino.id


class TestBusquedaDelTecnicoDestino:
    """El servicio solo valida que el id del técnico EXISTA (eso requiere al
    repositorio). Si ese usuario puede o no recibir el ticket lo decide el
    dominio: ver `test_requerimientos_dominio.py::TestTecnicoDestino`."""

    def test_asignar_a_un_id_inexistente_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante: Solicitante,
        operador: Operador,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)
        servicio.iniciar_analisis(requerimiento.id, operador)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.asignar_tecnico(requerimiento.id, uuid.uuid4(), operador)
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id is None

    def test_derivar_a_un_id_inexistente_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        solicitante: Solicitante,
        operador: Operador,
        tecnico: Tecnico,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante.id)
        servicio.iniciar_analisis(requerimiento.id, operador)
        servicio.asignar_tecnico(requerimiento.id, tecnico.id, operador)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.derivar_interconsulta(requerimiento.id, uuid.uuid4(), tecnico)

    def test_si_el_dominio_rechaza_el_destino_no_se_persiste_el_cambio(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        repo_usuarios: FakeRepositorioUsuarios,
        solicitante: Solicitante,
        operador: Operador,
        tecnico: Tecnico,
    ) -> None:
        # Arrange: el destino existe, pero el dominio no lo acepta (no es Técnico)
        repo_usuarios.guardar(operador)
        requerimiento = _crear_incidente(servicio, solicitante.id)
        servicio.iniciar_analisis(requerimiento.id, operador)
        servicio.asignar_tecnico(requerimiento.id, tecnico.id, operador)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.derivar_interconsulta(requerimiento.id, operador.id, tecnico)
        persistido = repositorio.buscar_por_id(requerimiento.id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id == tecnico.id
