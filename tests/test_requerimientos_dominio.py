"""Tests de dominio del módulo `app/requerimientos/`.

Cubre la creación polimórfica (`FabricaRequerimientos`), las invariantes de
las entidades concretas (`Incidente`, `Solicitud`) y la máquina de estados
con sus reglas de permisos por rol (`Requerimiento`).
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.dominio import RolUsuario
from app.requerimientos.dominio import (
    CategoriaSolicitud,
    EstadoRequerimiento,
    Incidente,
    Severidad,
    Solicitud,
    TipoRequerimiento,
)
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    NotaResolucionRequeridaError,
    PermisoDenegadoError,
    TecnicoNoAsignadoError,
    TransicionInvalidaError,
)
from app.requerimientos.fabrica import FabricaRequerimientos


@pytest.fixture
def solicitante_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def tecnico_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def incidente(solicitante_id: uuid.UUID) -> Incidente:
    # Arrange: incidente recién creado (estado ABIERTO)
    return Incidente(
        titulo="Corte de fibra troncal",
        descripcion="Sin conectividad en el barrio Centro.",
        solicitante_id=solicitante_id,
        severidad=Severidad.CRITICA,
        pasos_reproduccion="Verificar ONT sin luz de señal.",
        servicio_afectado="Fibra óptica residencial",
    )


def _avanzar_hasta_en_progreso(incidente: Incidente, tecnico_id: uuid.UUID) -> None:
    """Helper de arrange: lleva un incidente ABIERTO hasta EN_PROGRESO."""
    incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
    incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
    incidente.iniciar_progreso(autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)


class TestIncidenteCreacion:
    def test_incidente_nace_abierto_con_evento_de_creacion(self, incidente: Incidente) -> None:
        # Assert
        assert incidente.estado == EstadoRequerimiento.ABIERTO
        assert incidente.tipo == TipoRequerimiento.INCIDENTE
        assert len(incidente.historial) == 1
        assert incidente.historial[0].tipo_evento.value == "CREACION"

    def test_severidad_invalida_lanza_type_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                severidad="CRITICA",  # type: ignore[arg-type]
                pasos_reproduccion="pasos",
                servicio_afectado="TV",
            )

    def test_pasos_reproduccion_vacios_lanza_value_error(self, solicitante_id: uuid.UUID) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            Incidente(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                severidad=Severidad.BAJA,
                pasos_reproduccion="   ",
                servicio_afectado="TV",
            )


class TestSolicitudCreacion:
    def test_solicitud_valida_nace_abierta(self, solicitante_id: uuid.UUID) -> None:
        # Arrange
        fecha_limite = datetime.now(UTC) + timedelta(days=5)

        # Act
        solicitud = Solicitud(
            titulo="Alta de nuevo abono",
            descripcion="Cliente solicita nueva conexión.",
            solicitante_id=solicitante_id,
            categoria=CategoriaSolicitud.NUEVO_SERVICIO,
            fecha_limite=fecha_limite,
            impacto_estimado="Bajo",
        )

        # Assert
        assert solicitud.tipo == TipoRequerimiento.SOLICITUD
        assert solicitud.estado == EstadoRequerimiento.ABIERTO

    def test_fecha_limite_en_el_pasado_lanza_value_error(self, solicitante_id: uuid.UUID) -> None:
        # Arrange
        fecha_pasada = datetime.now(UTC) - timedelta(days=1)

        # Act & Assert
        with pytest.raises(ValueError):
            Solicitud(
                titulo="x",
                descripcion="y",
                solicitante_id=solicitante_id,
                categoria=CategoriaSolicitud.FACTURACION,
                fecha_limite=fecha_pasada,
                impacto_estimado="Bajo",
            )


class TestFlujoCompletoDeTransiciones:
    def test_flujo_completo_hasta_cierre(
        self, incidente: Incidente, solicitante_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> None:
        # Act
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver(
            "Se reemplazó el ONT dañado.", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
        )
        incidente.cerrar(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CERRADO
        assert incidente.tecnico_asignado_id == tecnico_id
        assert incidente.nota_resolucion == "Se reemplazó el ONT dañado."
        assert len(incidente.historial) == 6  # creación + 5 transiciones


class TestIniciarAnalisis:
    def test_solicitante_no_puede_iniciar_analisis(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_analisis(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)


class TestAsignarTecnico:
    def test_asignar_tecnico_antes_de_iniciar_analisis_lanza_transicion_invalida(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Act & Assert: el incidente sigue ABIERTO, no EN_ANALISIS
        with pytest.raises(TransicionInvalidaError):
            incidente.asignar_tecnico(
                tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
            )


class TestIniciarProgreso:
    def test_sin_tecnico_asignado_lanza_error(self, incidente: Incidente) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(TecnicoNoAsignadoError):
            incidente.iniciar_progreso(autor_id=uuid.uuid4(), rol_actor=RolUsuario.SUPERVISOR)

    def test_tecnico_distinto_al_asignado_lanza_permiso_denegado(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        otro_tecnico_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.iniciar_progreso(autor_id=otro_tecnico_id, rol_actor=RolUsuario.TECNICO)

    def test_supervisor_puede_iniciar_progreso_sin_ser_el_asignado(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act
        incidente.iniciar_progreso(autor_id=uuid.uuid4(), rol_actor=RolUsuario.SUPERVISOR)

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO


class TestResolver:
    def test_nota_vacia_lanza_error(self, incidente: Incidente, tecnico_id: uuid.UUID) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)

        # Act & Assert
        with pytest.raises(NotaResolucionRequeridaError):
            incidente.resolver("   ", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

    def test_operador_no_puede_resolver(self, incidente: Incidente, tecnico_id: uuid.UUID) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.resolver("Nota", autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)


class TestCerrar:
    def test_solicitante_ajeno_no_puede_cerrar(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)
        otro_solicitante_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cerrar(autor_id=otro_solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

    def test_tecnico_no_puede_cerrar(self, incidente: Incidente, tecnico_id: uuid.UUID) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cerrar(autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)


class TestCancelacion:
    def test_solicitante_puede_cancelar_mientras_esta_abierto(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Act
        incidente.cancelar(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CANCELADO

    def test_solicitante_no_puede_cancelar_en_analisis(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cancelar(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

    def test_operador_puede_cancelar_en_progreso(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)

        # Act
        incidente.cancelar(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Assert
        assert incidente.estado == EstadoRequerimiento.CANCELADO

    def test_tecnico_nunca_puede_cancelar(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.cancelar(autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

    def test_no_se_puede_cancelar_un_requerimiento_resuelto(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.cancelar(autor_id=uuid.uuid4(), rol_actor=RolUsuario.SUPERVISOR)


class TestHistorialEsUnaCopiaDefensiva:
    def test_mutar_la_lista_devuelta_no_afecta_al_original(self, incidente: Incidente) -> None:
        # Arrange
        historial = incidente.historial

        # Act
        historial.clear()

        # Assert
        assert len(incidente.historial) == 1


class TestFabricaRequerimientos:
    def test_crear_incidente_devuelve_instancia_incidente(self, solicitante_id: uuid.UUID) -> None:
        # Act
        req = FabricaRequerimientos.crear(
            TipoRequerimiento.INCIDENTE,
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            severidad=Severidad.MEDIA,
            pasos_reproduccion="p",
            servicio_afectado="s",
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
            categoria=CategoriaSolicitud.FACTURACION,
            fecha_limite=datetime.now(UTC) + timedelta(days=1),
            impacto_estimado="bajo",
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
    con el estado/historial real tal como estaba persistido)."""

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
            severidad=Severidad.CRITICA,
            pasos_reproduccion="Verificar ONT sin luz de señal.",
            servicio_afectado="Fibra óptica residencial",
        )

        # Assert: se restauró tal cual, sin generar un evento CREACION nuevo
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO
        assert incidente.fecha_creacion == fecha_creacion_original
        assert incidente.tecnico_asignado_id == tecnico_id
        assert incidente.historial == [evento_original]
        assert incidente.severidad == Severidad.CRITICA

    def test_incidente_reconstruido_sigue_pudiendo_transicionar(
        self, solicitante_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente = Incidente.reconstruir(
            id=uuid.uuid4(),
            titulo="x",
            descripcion="y",
            solicitante_id=solicitante_id,
            estado=EstadoRequerimiento.EN_PROGRESO,
            fecha_creacion=datetime.now(UTC),
            tecnico_asignado_id=tecnico_id,
            nota_resolucion=None,
            historial=[],
            severidad=Severidad.BAJA,
            pasos_reproduccion="p",
            servicio_afectado="s",
        )

        # Act
        incidente.resolver("Resuelto tras reconstrucción.", tecnico_id, RolUsuario.TECNICO)

        # Assert
        assert incidente.estado == EstadoRequerimiento.RESUELTO

    def test_reconstruir_solicitud_permite_fecha_limite_pasada(
        self, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange: una solicitud histórica cuyo plazo ya venció (el
        # constructor normal la rechazaría por `_validar_fecha_limite`)
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
            categoria=CategoriaSolicitud.NUEVO_SERVICIO,
            fecha_limite=fecha_pasada,
            impacto_estimado="Bajo",
        )

        # Assert
        assert solicitud.fecha_limite == fecha_pasada
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
            severidad=Severidad.MEDIA,
            pasos_reproduccion="p",
            servicio_afectado="s",
        )

        # Assert
        assert isinstance(req, Incidente)
