"""Tests de dominio del módulo `app/requerimientos/`.

Cubre la creación polimórfica (`FabricaRequerimientos`), las invariantes de
las entidades concretas (`Incidente`, `Solicitud`) y la máquina de estados
de `Requerimiento`: qué transición es válida desde cada estado y que el
ticket le PREGUNTE al actor (un `Usuario` real de cada rol) si puede
ejecutarla, incluyendo comentarios (con reapertura de un `RESUELTO`),
derivación/interconsulta, visibilidad y validez del técnico destino.

La matriz completa de "qué puede cada rol" se prueba rol por rol en
`test_usuarios_dominio.py`; acá se prueba que el ticket la respete.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.dominio import ServicioComunicarlos
from app.requerimientos.dominio import (
    CategoriaIncidente,
    CategoriaSolicitud,
    EstadoRequerimiento,
    Incidente,
    Solicitud,
    TipoRequerimiento,
    UrgenciaIncidente,
)
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    TecnicoInvalidoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)
from app.requerimientos.fabrica import FabricaRequerimientos
from app.usuarios.dominio import Operador, Solicitante, Supervisor, Tecnico, Usuario
from tests.actores import un_operador, un_solicitante, un_supervisor, un_tecnico


@pytest.fixture
def solicitante() -> Solicitante:
    return un_solicitante()


@pytest.fixture
def otro_solicitante() -> Solicitante:
    return un_solicitante(email="marcos@gmail.com")


@pytest.fixture
def operador() -> Operador:
    return un_operador()


@pytest.fixture
def tecnico() -> Tecnico:
    return un_tecnico()


@pytest.fixture
def otro_tecnico() -> Tecnico:
    return un_tecnico(email="marta@comunicarlos.com.ar")


@pytest.fixture
def supervisor() -> Supervisor:
    return un_supervisor()


@pytest.fixture
def solicitante_id(solicitante: Solicitante) -> uuid.UUID:
    return solicitante.id


@pytest.fixture
def tecnico_id(tecnico: Tecnico) -> uuid.UUID:
    return tecnico.id


@pytest.fixture
def incidente(solicitante: Solicitante) -> Incidente:
    # Arrange: incidente recién creado (estado ABIERTO) por `solicitante`
    return Incidente(
        titulo="Corte de fibra troncal",
        descripcion="Sin conectividad en el barrio Centro.",
        solicitante_id=solicitante.id,
        urgencia=UrgenciaIncidente.CRITICO,
        categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
        servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        pasos_reproduccion="Verificar ONT sin luz de señal.",
    )


def _asignar(incidente: Incidente, tecnico: Tecnico) -> None:
    """Helper de arrange: lleva un incidente ABIERTO hasta EN_ANALISIS con técnico."""
    operador = un_operador()
    incidente.iniciar_analisis(operador)
    incidente.asignar_tecnico(tecnico, operador)


def _avanzar_hasta_en_progreso(incidente: Incidente, tecnico: Tecnico) -> None:
    """Helper de arrange: lleva un incidente ABIERTO hasta EN_PROGRESO."""
    _asignar(incidente, tecnico)
    incidente.iniciar_progreso(tecnico)


def _avanzar_hasta_resuelto(incidente: Incidente, tecnico: Tecnico) -> None:
    _avanzar_hasta_en_progreso(incidente, tecnico)
    incidente.resolver("Nota", tecnico)


class TestIncidenteCreacion:
    def test_incidente_nace_abierto_con_evento_de_creacion(self, incidente: Incidente) -> None:
        # Assert
        assert incidente.estado == EstadoRequerimiento.ABIERTO
        assert incidente.tipo == TipoRequerimiento.INCIDENTE
        assert len(incidente.historial) == 1
        assert incidente.historial[0].tipo_evento == TipoEventoRequerimiento.CREACION

    def test_urgencia_invalida_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                urgencia="CRITICO",  # type: ignore[arg-type]
                categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
                servicio=ServicioComunicarlos.TELEVISION,
                pasos_reproduccion="pasos",
            )

    def test_categoria_invalida_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                urgencia=UrgenciaIncidente.MENOR,
                categoria="SERVICIO_INACCESIBLE",  # type: ignore[arg-type]
                servicio=ServicioComunicarlos.TELEVISION,
                pasos_reproduccion="pasos",
            )

    def test_servicio_invalido_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                urgencia=UrgenciaIncidente.MENOR,
                categoria=CategoriaIncidente.BLOQUEO_SIM,
                servicio="TELEVISION",  # type: ignore[arg-type]
                pasos_reproduccion="pasos",
            )

    def test_titulo_vacio_lanza_value_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Incidente(
                titulo="   ",
                descripcion="y",
                solicitante_id=solicitante_id,
                urgencia=UrgenciaIncidente.MENOR,
                categoria=CategoriaIncidente.BLOQUEO_SIM,
                servicio=ServicioComunicarlos.TELEVISION,
                pasos_reproduccion="pasos",
            )

    def test_pasos_reproduccion_vacios_lanza_value_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                urgencia=UrgenciaIncidente.MENOR,
                categoria=CategoriaIncidente.BLOQUEO_SIM,
                servicio=ServicioComunicarlos.TELEVISION,
                pasos_reproduccion="   ",
            )


class TestSolicitudCreacion:
    def test_solicitud_valida_nace_abierta(self, solicitante_id: uuid.UUID) -> None:
        # Act
        solicitud = Solicitud(
            titulo="Alta de nuevo abono",
            descripcion="Cliente solicita nueva conexión.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.ALTA_SERVICIO,
            servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        )

        # Assert
        assert solicitud.tipo == TipoRequerimiento.SOLICITUD
        assert solicitud.estado == EstadoRequerimiento.ABIERTO

    def test_categoria_invalida_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Solicitud(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                categoria="ALTA_SERVICIO",  # type: ignore[arg-type]
                servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            )

    def test_servicio_invalido_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Solicitud(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                categoria=CategoriaSolicitud.BAJA_SERVICIO,
                servicio="TELEFONIA_CELULAR",  # type: ignore[arg-type]
            )


class TestPreguntasDelTicket:
    """Lo que los actores le consultan al ticket para responder sus permisos."""

    def test_pertenece_a_su_solicitante_y_no_a_otro(
        self, incidente: Incidente, solicitante: Solicitante, otro_solicitante: Solicitante
    ) -> None:
        # Assert
        assert incidente.pertenece_a(solicitante)
        assert not incidente.pertenece_a(otro_solicitante)

    def test_esta_asignado_solo_al_tecnico_asignado(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Assert
        assert incidente.esta_asignado_a(tecnico)
        assert not incidente.esta_asignado_a(otro_tecnico)

    def test_esta_abierto_solo_mientras_nadie_lo_tomo(
        self, incidente: Incidente, operador: Operador
    ) -> None:
        # Arrange
        assert incidente.esta_abierto()

        # Act
        incidente.iniciar_analisis(operador)

        # Assert
        assert not incidente.esta_abierto()


class TestFlujoCompletoDeTransiciones:
    def test_flujo_completo_hasta_cierre(
        self, incidente: Incidente, solicitante: Solicitante, tecnico: Tecnico
    ) -> None:
        # Act
        _avanzar_hasta_en_progreso(incidente, tecnico)
        incidente.resolver("Se reemplazó el ONT dañado.", tecnico)
        incidente.cerrar(solicitante)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CERRADO
        assert incidente.tecnico_asignado_id == tecnico.id
        assert incidente.nota_resolucion == "Se reemplazó el ONT dañado."
        assert len(incidente.historial) == 6  # creación + 5 transiciones

    def test_cada_evento_registra_como_autor_al_actor(
        self, incidente: Incidente, operador: Operador
    ) -> None:
        # Act
        evento = incidente.iniciar_analisis(operador)

        # Assert
        assert evento.autor_id == operador.id


class TestVisibilidad:
    def test_el_dueno_puede_consultarlo(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act & Assert: no lanza
        incidente.exigir_visible_para(solicitante)

    def test_un_solicitante_ajeno_no_puede_consultarlo(
        self, incidente: Incidente, otro_solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.exigir_visible_para(otro_solicitante)

    def test_cualquier_empleado_puede_consultarlo(
        self,
        incidente: Incidente,
        operador: Operador,
        tecnico: Tecnico,
        supervisor: Supervisor,
    ) -> None:
        # Act & Assert: no lanza
        for empleado in (operador, tecnico, supervisor):
            incidente.exigir_visible_para(empleado)


class TestIniciarAnalisis:
    def test_operador_inicia_el_analisis(self, incidente: Incidente, operador: Operador) -> None:
        # Act
        incidente.iniciar_analisis(operador)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_ANALISIS

    def test_solicitante_no_puede_iniciar_analisis(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_analisis(solicitante)
        assert incidente.estado == EstadoRequerimiento.ABIERTO

    def test_tecnico_no_puede_iniciar_analisis(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_analisis(tecnico)

    def test_no_se_puede_iniciar_dos_veces(
        self, incidente: Incidente, operador: Operador
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.iniciar_analisis(operador)


class TestAsignarTecnico:
    def test_asignar_tecnico_antes_de_iniciar_analisis_lanza_transicion_invalida(
        self, incidente: Incidente, operador: Operador, tecnico: Tecnico
    ) -> None:
        # Act & Assert: el incidente sigue ABIERTO, no EN_ANALISIS
        with pytest.raises(TransicionInvalidaError):
            incidente.asignar_tecnico(tecnico, operador)

    def test_tecnico_no_puede_autoasignarse(
        self, incidente: Incidente, operador: Operador, tecnico: Tecnico
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.asignar_tecnico(tecnico, tecnico)


class TestTecnicoDestino:
    """Solo se puede asignar o derivar un ticket a quien contesta que puede
    recibirlo (`puede_recibir_requerimientos()`): un Técnico activo. Sin esta
    regla, el ticket quedaría "asignado" a alguien que no puede trabajarlo
    y saldría del circuito técnico."""

    @pytest.mark.parametrize(
        "destino",
        [
            pytest.param(un_solicitante(), id="solicitante"),
            pytest.param(un_operador(), id="operador"),
            pytest.param(un_supervisor(), id="supervisor"),
        ],
    )
    def test_no_se_puede_asignar_a_quien_no_es_tecnico(
        self, incidente: Incidente, operador: Operador, destino: Usuario
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            incidente.asignar_tecnico(destino, operador)
        assert incidente.tecnico_asignado_id is None

    def test_no_se_puede_asignar_a_un_tecnico_desactivado(
        self, incidente: Incidente, operador: Operador
    ) -> None:
        # Arrange
        de_baja = un_tecnico(email="egresado@comunicarlos.com.ar", activo=False)
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            incidente.asignar_tecnico(de_baja, operador)

    def test_no_se_puede_derivar_a_quien_no_es_tecnico(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            incidente.derivar_interconsulta(operador, tecnico)
        assert incidente.esta_asignado_a(tecnico)

    def test_no_se_puede_derivar_a_un_tecnico_desactivado(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)
        de_baja = un_tecnico(email="egresado@comunicarlos.com.ar", activo=False)

        # Act & Assert
        with pytest.raises(TecnicoInvalidoError):
            incidente.derivar_interconsulta(de_baja, tecnico)


class TestIniciarProgreso:
    def test_sin_tecnico_asignado_lanza_error(
        self, incidente: Incidente, operador: Operador, supervisor: Supervisor
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(TecnicoNoAsignadoError):
            incidente.iniciar_progreso(supervisor)

    def test_tecnico_asignado_puede_iniciar_progreso(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act
        incidente.iniciar_progreso(tecnico)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO

    def test_tecnico_distinto_al_asignado_lanza_permiso_denegado(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_progreso(otro_tecnico)

    def test_operador_no_puede_iniciar_progreso(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_progreso(operador)

    def test_supervisor_puede_iniciar_progreso_sin_ser_el_asignado(
        self, incidente: Incidente, tecnico: Tecnico, supervisor: Supervisor
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act
        incidente.iniciar_progreso(supervisor)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO


class TestResolver:
    def test_nota_vacia_lanza_error(self, incidente: Incidente, tecnico: Tecnico) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico)

        # Act & Assert
        with pytest.raises(NotaResolucionRequeridaError):
            incidente.resolver("   ", tecnico)

    def test_operador_no_puede_resolver(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.resolver("Nota", operador)

    def test_supervisor_puede_resolver_sin_ser_el_asignado(
        self, incidente: Incidente, tecnico: Tecnico, supervisor: Supervisor
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico)

        # Act
        incidente.resolver("Resuelto por supervisión.", supervisor)

        # Assert
        assert incidente.estado == EstadoRequerimiento.RESUELTO


class TestCerrar:
    def test_operador_puede_dar_cierre_de_conformidad(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act
        incidente.cerrar(operador)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CERRADO

    def test_solicitante_ajeno_no_puede_cerrar(
        self, incidente: Incidente, tecnico: Tecnico, otro_solicitante: Solicitante
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cerrar(otro_solicitante)

    def test_tecnico_no_puede_cerrar(self, incidente: Incidente, tecnico: Tecnico) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cerrar(tecnico)

    def test_no_se_puede_cerrar_lo_que_no_esta_resuelto(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.cerrar(solicitante)


class TestCancelacion:
    def test_solicitante_puede_cancelar_mientras_esta_abierto(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act
        incidente.cancelar(solicitante)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CANCELADO

    def test_solicitante_no_puede_cancelar_en_analisis(
        self, incidente: Incidente, solicitante: Solicitante, operador: Operador
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(operador)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cancelar(solicitante)

    def test_solicitante_ajeno_no_puede_cancelar(
        self, incidente: Incidente, otro_solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cancelar(otro_solicitante)

    def test_operador_puede_cancelar_en_progreso(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico)

        # Act
        incidente.cancelar(operador)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CANCELADO

    def test_tecnico_nunca_puede_cancelar(self, incidente: Incidente, tecnico: Tecnico) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cancelar(tecnico)

    def test_no_se_puede_cancelar_un_requerimiento_resuelto(
        self, incidente: Incidente, tecnico: Tecnico, supervisor: Supervisor
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.cancelar(supervisor)


class TestAgregarComentario:
    def test_solicitante_dueno_puede_comentar(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act
        comentario = incidente.agregar_comentario("¿Alguna novedad?", solicitante)

        # Assert
        assert comentario.texto == "¿Alguna novedad?"
        assert comentario.autor_id == solicitante.id
        assert incidente.comentarios == [comentario]
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.COMENTARIO

    def test_solicitante_ajeno_no_puede_comentar(
        self, incidente: Incidente, otro_solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario("x", otro_solicitante)

    def test_operador_siempre_puede_comentar(
        self, incidente: Incidente, operador: Operador
    ) -> None:
        # Act
        comentario = incidente.agregar_comentario("Seguimiento del operador.", operador)

        # Assert
        assert comentario in incidente.comentarios

    def test_tecnico_no_asignado_no_puede_comentar(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange: incidente sin técnico asignado todavía
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario("x", tecnico)

    def test_tecnico_asignado_puede_comentar(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act
        comentario = incidente.agregar_comentario("Avanzando con el diagnóstico.", tecnico)

        # Assert
        assert comentario in incidente.comentarios

    def test_supervisor_nunca_puede_comentar(
        self, incidente: Incidente, supervisor: Supervisor
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario("x", supervisor)

    def test_texto_vacio_lanza_value_error(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            incidente.agregar_comentario("   ", solicitante)

    def test_no_se_puede_comentar_un_cerrado(
        self, incidente: Incidente, solicitante: Solicitante, tecnico: Tecnico
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)
        incidente.cerrar(solicitante)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.agregar_comentario("x", solicitante)

    def test_no_se_puede_comentar_un_cancelado(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Arrange
        incidente.cancelar(solicitante)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.agregar_comentario("x", solicitante)

    def test_comentario_de_operador_reabre_un_resuelto(
        self, incidente: Incidente, tecnico: Tecnico, operador: Operador
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act
        incidente.agregar_comentario("No quedó resuelto, vuelvo a abrir.", operador)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.REAPERTURA
        assert incidente.historial[-2].tipo_evento == TipoEventoRequerimiento.COMENTARIO

    def test_comentario_de_tecnico_asignado_reabre_un_resuelto(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act
        incidente.agregar_comentario("Falta un ajuste más.", tecnico)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO

    def test_comentario_de_solicitante_no_reabre_un_resuelto(
        self, incidente: Incidente, solicitante: Solicitante, tecnico: Tecnico
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act
        incidente.agregar_comentario("Gracias, quedó resuelto.", solicitante)

        # Assert: el comentario del dueño no reabre el ticket
        assert incidente.estado == EstadoRequerimiento.RESUELTO
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.COMENTARIO


class TestDerivarInterconsulta:
    def test_tecnico_asignado_puede_derivar(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act
        incidente.derivar_interconsulta(otro_tecnico, tecnico)

        # Assert
        assert incidente.esta_asignado_a(otro_tecnico)
        assert not incidente.esta_asignado_a(tecnico)
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.DERIVACION

    def test_tecnico_no_asignado_no_puede_derivar(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.derivar_interconsulta(un_tecnico(email="x@comunicarlos.com.ar"), otro_tecnico)

    def test_supervisor_no_puede_derivar(
        self,
        incidente: Incidente,
        tecnico: Tecnico,
        otro_tecnico: Tecnico,
        supervisor: Supervisor,
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.derivar_interconsulta(otro_tecnico, supervisor)

    def test_no_se_puede_derivar_al_mismo_tecnico(
        self, incidente: Incidente, tecnico: Tecnico
    ) -> None:
        # Arrange
        _asignar(incidente, tecnico)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(tecnico, tecnico)

    def test_no_se_puede_derivar_en_abierto(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Act & Assert: todavía no hay técnico asignado ni tiene sentido derivar
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(otro_tecnico, tecnico)

    def test_no_se_puede_derivar_un_resuelto(
        self, incidente: Incidente, tecnico: Tecnico, otro_tecnico: Tecnico
    ) -> None:
        # Arrange
        _avanzar_hasta_resuelto(incidente, tecnico)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(otro_tecnico, tecnico)


class TestHistorialEsUnaCopiaDefensiva:
    def test_mutar_la_lista_devuelta_no_afecta_al_original(self, incidente: Incidente) -> None:
        # Arrange
        historial = incidente.historial

        # Act
        historial.clear()

        # Assert
        assert len(incidente.historial) == 1

    def test_mutar_la_lista_de_comentarios_no_afecta_al_original(
        self, incidente: Incidente, solicitante: Solicitante
    ) -> None:
        # Arrange
        incidente.agregar_comentario("x", solicitante)
        comentarios = incidente.comentarios

        # Act
        comentarios.clear()

        # Assert
        assert len(incidente.comentarios) == 1


class TestFabricaRequerimientos:
    def test_crear_incidente_devuelve_instancia_incidente(self, solicitante_id: uuid.UUID) -> None:
        # Act
        req = FabricaRequerimientos.crear(
            TipoRequerimiento.INCIDENTE,
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            urgencia=UrgenciaIncidente.IMPORTANTE,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            pasos_reproduccion="p",
        )

        # Assert
        assert isinstance(req, Incidente)
        assert req.tipo == TipoRequerimiento.INCIDENTE

    def test_crear_solicitud_devuelve_instancia_solicitud(self, solicitante_id: uuid.UUID) -> None:
        # Act
        req = FabricaRequerimientos.crear(
            TipoRequerimiento.SOLICITUD,
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.BAJA_SERVICIO,
            servicio=ServicioComunicarlos.TELEVISION,
        )

        # Assert
        assert isinstance(req, Solicitud)
        assert req.tipo == TipoRequerimiento.SOLICITUD

    def test_tipo_no_soportado_lanza_value_error(self) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            FabricaRequerimientos.crear("TIPO_INEXISTENTE")  # type: ignore[arg-type]


class TestReconstruccionDesdePersistencia:
    """Cubre `reconstruir`: la vía de lectura desde Mongo (Paso 5), que NO
    debe comportarse como una creación nueva (sin evento CREACION espurio,
    con el estado/historial/comentarios real tal como estaba persistido)."""

    def test_reconstruir_incidente_no_agrega_evento_creacion(
        self, solicitante_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange: un evento de historial "real" ya persistido, distinto al
        # que generaría un __init__ nuevo.
        evento_original = EventoRequerimiento(
            requerimiento_id=uuid.uuid4(),
            tipo_evento=TipoEventoRequerimiento.CREACION,
            autor_id=solicitante_id,
            detalle="Evento tal cual vino de Mongo.",
        )
        fecha_creacion_original = datetime.now(UTC) - timedelta(days=10)

        # Act
        incidente = Incidente.reconstruir(
            id=uuid.uuid4(),
            titulo="Corte de fibra troncal",
            descripcion="Sin conectividad en el barrio Centro.",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.EN_PROGRESO,
            fecha_creacion=fecha_creacion_original,
            tecnico_asignado_id=tecnico_id,
            nota_resolucion=None,
            historial=[evento_original],
            urgencia=UrgenciaIncidente.CRITICO,
            categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
            servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
            pasos_reproduccion="Verificar ONT sin luz de señal.",
        )

        # Assert: se restauró tal cual, sin generar un evento CREACION nuevo
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO
        assert incidente.fecha_creacion == fecha_creacion_original
        assert incidente.tecnico_asignado_id == tecnico_id
        assert incidente.historial == [evento_original]
        assert incidente.comentarios == []
        assert incidente.urgencia == UrgenciaIncidente.CRITICO

    def test_reconstruir_incidente_restaura_comentarios(
        self, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        from app.requerimientos.dominio.comentario import Comentario

        comentario_original = Comentario(
            requerimiento_id=uuid.uuid4(), autor_id=solicitante_id, texto="Comentario persistido."
        )

        # Act
        incidente = Incidente.reconstruir(
            id=uuid.uuid4(),
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.ABIERTO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=None,
            nota_resolucion=None,
            historial=[],
            comentarios=[comentario_original],
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            pasos_reproduccion="p",
        )

        # Assert
        assert incidente.comentarios == [comentario_original]

    def test_incidente_reconstruido_sigue_pudiendo_transicionar(
        self, solicitante_id: uuid.UUID, tecnico: Tecnico
    ) -> None:
        # Arrange
        incidente = Incidente.reconstruir(
            id=uuid.uuid4(),
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.EN_PROGRESO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=tecnico.id,
            nota_resolucion=None,
            historial=[],
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            pasos_reproduccion="p",
        )

        # Act
        incidente.resolver("Resuelto tras reconstrucción.", tecnico)

        # Assert
        assert incidente.estado == EstadoRequerimiento.RESUELTO

    def test_reconstruir_solicitud(self, solicitante_id: uuid.UUID) -> None:
        # Arrange: una solicitud histórica ya cerrada
        fecha_pasada = datetime.now(UTC) - timedelta(days=30)

        # Act
        solicitud = Solicitud.reconstruir(
            id=uuid.uuid4(),
            titulo="Alta de nuevo abono",
            descripcion="Cliente solicita nueva conexión.",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.CERRADO,
            fecha_creacion=fecha_pasada,
            tecnico_asignado_id=None,
            nota_resolucion=None,
            historial=[],
            categoria=CategoriaSolicitud.ALTA_SERVICIO,
            servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        )

        # Assert
        assert solicitud.categoria == CategoriaSolicitud.ALTA_SERVICIO
        assert solicitud.estado == EstadoRequerimiento.CERRADO

    def test_fabrica_reconstruir_dispatchea_por_tipo(self, solicitante_id: uuid.UUID) -> None:
        # Act
        req = FabricaRequerimientos.reconstruir(
            TipoRequerimiento.INCIDENTE,
            id=uuid.uuid4(),
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.ABIERTO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=None,
            nota_resolucion=None,
            historial=[],
            urgencia=UrgenciaIncidente.IMPORTANTE,
            categoria=CategoriaIncidente.PERDIDA_O_DESTRUCCION_DE_EQUIPO,
            servicio=ServicioComunicarlos.TELEVISION,
            pasos_reproduccion="p",
        )

        # Assert
        assert isinstance(req, Incidente)
