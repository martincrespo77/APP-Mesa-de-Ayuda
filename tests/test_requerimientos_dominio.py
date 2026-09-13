"""Tests de dominio del módulo `app/requerimientos/`.

Cubre la creación polimórfica (`FabricaRequerimientos`), las invariantes de
las entidades concretas (`Incidente`, `Solicitud`) y la máquina de estados
con sus reglas de permisos por rol (`Requerimiento`), incluyendo comentarios
(con reapertura de un `RESUELTO`) y derivación/interconsulta entre técnicos.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
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
        urgencia=UrgenciaIncidente.CRITICO,
        categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
        servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        pasos_reproduccion="Verificar ONT sin luz de señal.",
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


class TestAgregarComentario:
    def test_solicitante_dueno_puede_comentar(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Act
        comentario = incidente.agregar_comentario(
            "¿Alguna novedad?", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE
        )

        # Assert
        assert comentario.texto == "¿Alguna novedad?"
        assert incidente.comentarios == [comentario]
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.COMENTARIO

    def test_solicitante_ajeno_no_puede_comentar(self, incidente: Incidente) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario(
                "x", autor_id=uuid.uuid4(), rol_actor=RolUsuario.SOLICITANTE
            )

    def test_operador_siempre_puede_comentar(self, incidente: Incidente) -> None:
        # Act
        comentario = incidente.agregar_comentario(
            "Seguimiento del operador.", autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
        )

        # Assert
        assert comentario in incidente.comentarios

    def test_tecnico_no_asignado_no_puede_comentar(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange: incidente sin técnico asignado todavía
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario("x", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

    def test_tecnico_asignado_puede_comentar(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act
        comentario = incidente.agregar_comentario(
            "Avanzando con el diagnóstico.", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
        )

        # Assert
        assert comentario in incidente.comentarios

    def test_supervisor_nunca_puede_comentar(self, incidente: Incidente) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.agregar_comentario(
                "x", autor_id=uuid.uuid4(), rol_actor=RolUsuario.SUPERVISOR
            )

    def test_texto_vacio_lanza_value_error(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Act & Assert
        with pytest.raises(ValueError):
            incidente.agregar_comentario(
                "   ", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE
            )

    def test_no_se_puede_comentar_un_cerrado(
        self, incidente: Incidente, solicitante_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)
        incidente.cerrar(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.agregar_comentario(
                "x", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE
            )

    def test_no_se_puede_comentar_un_cancelado(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.cancelar(autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.agregar_comentario(
                "x", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE
            )

    def test_comentario_de_operador_reabre_un_resuelto(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act
        incidente.agregar_comentario(
            "No quedó resuelto, vuelvo a abrir.",
            autor_id=uuid.uuid4(),
            rol_actor=RolUsuario.OPERADOR,
        )

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.REAPERTURA
        assert incidente.historial[-2].tipo_evento == TipoEventoRequerimiento.COMENTARIO

    def test_comentario_de_tecnico_asignado_reabre_un_resuelto(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act
        incidente.agregar_comentario(
            "Falta un ajuste más.", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
        )

        # Assert
        assert incidente.estado == EstadoRequerimiento.EN_PROGRESO

    def test_comentario_de_solicitante_no_reabre_un_resuelto(
        self, incidente: Incidente, solicitante_id: uuid.UUID, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act
        incidente.agregar_comentario(
            "Gracias, quedó resuelto.", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE
        )

        # Assert: el comentario del dueño no reabre el ticket
        assert incidente.estado == EstadoRequerimiento.RESUELTO
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.COMENTARIO


class TestDerivarInterconsulta:
    def test_tecnico_asignado_puede_derivar(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        tecnico_destino_id = uuid.uuid4()

        # Act
        incidente.derivar_interconsulta(
            tecnico_destino_id, autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
        )

        # Assert
        assert incidente.tecnico_asignado_id == tecnico_destino_id
        assert incidente.historial[-1].tipo_evento == TipoEventoRequerimiento.DERIVACION

    def test_tecnico_no_asignado_no_puede_derivar(self, incidente: Incidente) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(
            uuid.uuid4(), autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR
        )

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.derivar_interconsulta(
                uuid.uuid4(), autor_id=uuid.uuid4(), rol_actor=RolUsuario.TECNICO
            )

    def test_otro_rol_no_puede_derivar(self, incidente: Incidente, tecnico_id: uuid.UUID) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            incidente.derivar_interconsulta(
                uuid.uuid4(), autor_id=uuid.uuid4(), rol_actor=RolUsuario.SUPERVISOR
            )

    def test_no_se_puede_derivar_al_mismo_tecnico(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.iniciar_analisis(autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)
        incidente.asignar_tecnico(tecnico_id, autor_id=uuid.uuid4(), rol_actor=RolUsuario.OPERADOR)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(
                tecnico_id, autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
            )

    def test_no_se_puede_derivar_en_abierto(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Act & Assert: todavía no hay técnico asignado ni tiene sentido derivar
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(
                uuid.uuid4(), autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
            )

    def test_no_se_puede_derivar_un_resuelto(
        self, incidente: Incidente, tecnico_id: uuid.UUID
    ) -> None:
        # Arrange
        _avanzar_hasta_en_progreso(incidente, tecnico_id)
        incidente.resolver("Nota", autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO)

        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            incidente.derivar_interconsulta(
                uuid.uuid4(), autor_id=tecnico_id, rol_actor=RolUsuario.TECNICO
            )


class TestHistorialEsUnaCopiaDefensiva:
    def test_mutar_la_lista_devuelta_no_afecta_al_original(self, incidente: Incidente) -> None:
        # Arrange
        historial = incidente.historial

        # Act
        historial.clear()

        # Assert
        assert len(incidente.historial) == 1

    def test_mutar_la_lista_de_comentarios_no_afecta_al_original(
        self, incidente: Incidente, solicitante_id: uuid.UUID
    ) -> None:
        # Arrange
        incidente.agregar_comentario("x", autor_id=solicitante_id, rol_actor=RolUsuario.SOLICITANTE)
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
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            servicio=ServicioComunicarlos.TELEFONIA_CELULAR,
            pasos_reproduccion="p",
        )

        # Act
        incidente.resolver("Resuelto tras reconstrucción.", tecnico_id, RolUsuario.TECNICO)

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
