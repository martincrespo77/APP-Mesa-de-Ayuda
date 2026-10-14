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
from app.requerimientos.excepciones import (
    PermisoDenegadoError,
    RequerimientoNoEncontradoError,
    TecnicoInvalidoError,
)
from app.requerimientos.servicios import ServicioRequerimientos
from app.usuarios.dominio import Usuario
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


def _alta_usuario(
    repo: FakeRepositorioUsuarios, email: str, rol: RolUsuario, activo: bool = True
) -> Usuario:
    """Da de alta un usuario real en el repositorio fake.

    `asignar_tecnico`/`derivar_interconsulta` ahora exigen que el destino
    sea un Técnico activo existente, así que los tests ya no pueden pasar
    un `uuid.uuid4()` suelto como id de técnico.
    """
    servicios = (
        frozenset({ServicioComunicarlos.INTERNET_BANDA_ANCHA})
        if rol == RolUsuario.SOLICITANTE
        else frozenset()
    )
    usuario = Usuario(
        email.split("@")[0], email, "hash-irrelevante", rol, servicios_suscriptos=servicios
    )
    if not activo:
        usuario.desactivar()
    repo.guardar(usuario)
    return usuario


@pytest.fixture
def tecnico(repo_usuarios: FakeRepositorioUsuarios) -> Usuario:
    return _alta_usuario(repo_usuarios, "ivan.rios@comunicarlos.com.ar", RolUsuario.TECNICO)


@pytest.fixture
def tecnico_destino(repo_usuarios: FakeRepositorioUsuarios) -> Usuario:
    return _alta_usuario(repo_usuarios, "marta.suarez@comunicarlos.com.ar", RolUsuario.TECNICO)


@pytest.fixture
def servicio(
    repositorio: FakeRepositorioRequerimientos,
    despachador: DespachadorEventos,
    repo_usuarios: FakeRepositorioUsuarios,
) -> ServicioRequerimientos:
    return ServicioRequerimientos(repositorio, despachador, repo_usuarios)


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
        tecnico: Usuario,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_id = tecnico.id

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
        tecnico: Usuario,
    ) -> None:
        # Arrange: lleva el incidente hasta RESUELTO
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_id = tecnico.id
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
        tecnico: Usuario,
        tecnico_destino: Usuario,
    ) -> None:
        # Arrange
        requerimiento = _crear_incidente(servicio, solicitante_id)
        tecnico_origen_id = tecnico.id
        tecnico_destino_id = tecnico_destino.id
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


class TestValidacionDelTecnicoDestino:
    """`asignar_tecnico` y `derivar_interconsulta` solo aceptan Técnicos activos.

    La entidad no puede validarlo (dominio puro, sin acceso a usuarios), así
    que la regla vive en el servicio. Sin ella, un ticket puede quedar
    "asignado" a un Solicitante o a un UUID inexistente y salirse del
    circuito técnico: el asignado no puede iniciar progreso ni derivar.
    """

    def _en_analisis(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> uuid.UUID:
        requerimiento = _crear_incidente(servicio, solicitante_id)
        servicio.iniciar_analisis(requerimiento.id, uuid.uuid4(), RolUsuario.OPERADOR)
        return requerimiento.id

    def test_asignar_a_un_id_inexistente_lanza_tecnico_invalido(
        self, servicio: ServicioRequerimientos, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        requerimiento_id = self._en_analisis(servicio, solicitante_id)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.asignar_tecnico(
                requerimiento_id, uuid.uuid4(), uuid.uuid4(), RolUsuario.OPERADOR
            )

    def test_asignar_a_un_solicitante_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        repo_usuarios: FakeRepositorioUsuarios,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Arrange: un usuario real, pero con rol SOLICITANTE
        no_tecnico = _alta_usuario(repo_usuarios, "lucia.gomez@mail.com", RolUsuario.SOLICITANTE)
        requerimiento_id = self._en_analisis(servicio, solicitante_id)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.asignar_tecnico(
                requerimiento_id, no_tecnico.id, uuid.uuid4(), RolUsuario.OPERADOR
            )

    def test_asignar_a_un_tecnico_desactivado_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        repo_usuarios: FakeRepositorioUsuarios,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Arrange
        de_baja = _alta_usuario(
            repo_usuarios, "egresado@comunicarlos.com.ar", RolUsuario.TECNICO, activo=False
        )
        requerimiento_id = self._en_analisis(servicio, solicitante_id)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.asignar_tecnico(
                requerimiento_id, de_baja.id, uuid.uuid4(), RolUsuario.OPERADOR
            )

    def test_asignar_no_muta_el_requerimiento_si_el_destino_es_invalido(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        solicitante_id: uuid.UUID,
    ) -> None:
        # Arrange
        requerimiento_id = self._en_analisis(servicio, solicitante_id)

        # Act
        with pytest.raises(TecnicoInvalidoError):
            servicio.asignar_tecnico(
                requerimiento_id, uuid.uuid4(), uuid.uuid4(), RolUsuario.OPERADOR
            )

        # Assert: se rechaza ANTES de tocar la entidad
        persistido = repositorio.buscar_por_id(requerimiento_id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id is None
        assert persistido.estado == EstadoRequerimiento.EN_ANALISIS

    def test_derivar_a_un_id_inexistente_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        solicitante_id: uuid.UUID,
        tecnico: Usuario,
    ) -> None:
        # Arrange
        requerimiento_id = self._en_analisis(servicio, solicitante_id)
        servicio.asignar_tecnico(requerimiento_id, tecnico.id, uuid.uuid4(), RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.derivar_interconsulta(
                requerimiento_id, uuid.uuid4(), tecnico.id, RolUsuario.TECNICO
            )

    def test_derivar_a_un_no_tecnico_lanza_tecnico_invalido(
        self,
        servicio: ServicioRequerimientos,
        repositorio: FakeRepositorioRequerimientos,
        repo_usuarios: FakeRepositorioUsuarios,
        solicitante_id: uuid.UUID,
        tecnico: Usuario,
    ) -> None:
        # Arrange
        operador = _alta_usuario(repo_usuarios, "rosa@comunicarlos.com.ar", RolUsuario.OPERADOR)
        requerimiento_id = self._en_analisis(servicio, solicitante_id)
        servicio.asignar_tecnico(requerimiento_id, tecnico.id, uuid.uuid4(), RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            servicio.derivar_interconsulta(
                requerimiento_id, operador.id, tecnico.id, RolUsuario.TECNICO
            )

        # El técnico original sigue asignado: la derivación no se aplicó
        persistido = repositorio.buscar_por_id(requerimiento_id)
        assert persistido is not None
        assert persistido.tecnico_asignado_id == tecnico.id
