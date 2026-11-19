"""Tests de dominio del Patrón State, de la autovalidación de los Value
Objects del agregado (`Comentario`, `EventoRequerimiento`) y de las
exigencias Tell, Don't Ask del `Usuario`.

Las transiciones completas del ticket se prueban en
`test_requerimientos_dominio.py`; acá se prueba cada pieza aislada.
"""

import uuid

import pytest

from app.compartido.dominio import ServicioComunicarlos
from app.compartido.excepciones import DatoInvalidoError
from app.requerimientos.dominio import (
    CategoriaIncidente,
    Comentario,
    DatosIncidente,
    EstadoRequerimiento,
    Incidente,
    UrgenciaIncidente,
)
from app.requerimientos.dominio.estados import (
    EstadoAbierto,
    EstadoCancelado,
    EstadoCerrado,
    EstadoEnAnalisis,
    EstadoEnProgreso,
    EstadoResuelto,
    EstadoTicket,
    FabricaEstados,
)
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.excepciones import (
    PermisoDenegadoError,
    TecnicoInvalidoError,
    TransicionInvalidaError,
)
from app.supervision.excepciones import RolNoSupervisableError
from app.usuarios.dominio import Tecnico
from tests.actores import un_operador, un_solicitante, un_supervisor, un_tecnico


def _ticket_resuelto_por(tecnico: Tecnico) -> Incidente:
    ticket = DatosIncidente(
        titulo="Sin internet",
        descripcion="No navega.",
        servicio=ServicioComunicarlos.INTERNET_BANDA_ANCHA,
        urgencia=UrgenciaIncidente.MENOR,
        categoria=CategoriaIncidente.SERVICIO_INACCESIBLE,
        pasos_reproduccion="Reiniciar.",
    ).construir_para(un_solicitante())
    operador = un_operador()
    ticket.iniciar_analisis(operador)
    ticket.asignar_tecnico(tecnico, operador)
    ticket.iniciar_progreso(tecnico)
    ticket.resolver("Se cambió el ONT.", tecnico)
    return ticket


class TestFabricaEstados:
    @pytest.mark.parametrize("codigo", list(EstadoRequerimiento))
    def test_hidrata_cada_codigo_en_un_estado_con_ese_mismo_codigo(
        self, codigo: EstadoRequerimiento
    ) -> None:
        # Act
        estado = FabricaEstados.desde_codigo(codigo)

        # Assert
        assert isinstance(estado, EstadoTicket)
        assert estado.codigo == codigo

    def test_el_estado_inicial_es_abierto(self) -> None:
        # Assert
        assert isinstance(FabricaEstados.inicial(), EstadoAbierto)

    def test_un_codigo_crudo_lanza_type_error(self) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            FabricaEstados.desde_codigo("ABIERTO")  # type: ignore[arg-type]


class TestTransicionesPorEstado:
    """Cada estado solo implementa las transiciones válidas desde sí mismo."""

    def test_camino_feliz_del_ciclo_de_vida(self) -> None:
        # Act
        en_analisis = EstadoAbierto().iniciar_analisis()
        en_progreso = en_analisis.iniciar_progreso()
        resuelto = en_progreso.resolver()
        cerrado = resuelto.cerrar()

        # Assert
        assert isinstance(en_analisis, EstadoEnAnalisis)
        assert isinstance(en_progreso, EstadoEnProgreso)
        assert isinstance(resuelto, EstadoResuelto)
        assert isinstance(cerrado, EstadoCerrado)

    def test_resuelto_se_puede_reabrir_a_en_progreso(self) -> None:
        # Assert
        assert isinstance(EstadoResuelto().reabrir(), EstadoEnProgreso)

    @pytest.mark.parametrize("estado", [EstadoAbierto(), EstadoEnAnalisis(), EstadoEnProgreso()])
    def test_los_estados_no_resueltos_se_pueden_cancelar(self, estado: EstadoTicket) -> None:
        # Assert
        assert isinstance(estado.cancelar(), EstadoCancelado)

    @pytest.mark.parametrize("estado", [EstadoResuelto(), EstadoCerrado(), EstadoCancelado()])
    def test_los_estados_resueltos_o_terminales_no_se_pueden_cancelar(
        self, estado: EstadoTicket
    ) -> None:
        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            estado.cancelar()

    @pytest.mark.parametrize("estado", [EstadoCerrado(), EstadoCancelado()])
    @pytest.mark.parametrize(
        "transicion",
        ["iniciar_analisis", "iniciar_progreso", "resolver", "cerrar", "cancelar", "reabrir"],
    )
    def test_los_estados_terminales_rechazan_toda_transicion(
        self, estado: EstadoTicket, transicion: str
    ) -> None:
        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            getattr(estado, transicion)()

    @pytest.mark.parametrize("estado", [EstadoCerrado(), EstadoCancelado()])
    def test_los_estados_terminales_no_admiten_comentarios(self, estado: EstadoTicket) -> None:
        # Act & Assert
        with pytest.raises(TransicionInvalidaError):
            estado.exigir_admite_comentarios()

    def test_solo_en_analisis_admite_asignacion(self) -> None:
        # Act: no lanza
        EstadoEnAnalisis().exigir_admite_asignacion()

        # Assert
        for estado in (EstadoAbierto(), EstadoEnProgreso(), EstadoResuelto()):
            with pytest.raises(TransicionInvalidaError):
                estado.exigir_admite_asignacion()

    def test_solo_los_estados_en_atencion_admiten_derivacion(self) -> None:
        # Act: no lanzan
        EstadoEnAnalisis().exigir_admite_derivacion()
        EstadoEnProgreso().exigir_admite_derivacion()

        # Assert
        for estado in (EstadoAbierto(), EstadoResuelto(), EstadoCerrado()):
            with pytest.raises(TransicionInvalidaError):
                estado.exigir_admite_derivacion()

    def test_solo_abierto_esta_abierto(self) -> None:
        # Assert
        assert EstadoAbierto().esta_abierto()
        assert not any(
            estado.esta_abierto()
            for estado in (EstadoEnAnalisis(), EstadoEnProgreso(), EstadoResuelto())
        )


class TestComentarioAutovalidado:
    def test_normaliza_el_texto(self) -> None:
        # Act
        comentario = Comentario(
            requerimiento_id=uuid.uuid4(), autor_id=uuid.uuid4(), texto="  hola  "
        )

        # Assert
        assert comentario.texto == "hola"

    def test_texto_vacio_lanza_dato_invalido(self) -> None:
        # Act & Assert
        with pytest.raises(DatoInvalidoError):
            Comentario(requerimiento_id=uuid.uuid4(), autor_id=uuid.uuid4(), texto="   ")

    def test_autor_que_no_es_uuid_lanza_type_error(self) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            Comentario(
                requerimiento_id=uuid.uuid4(),
                autor_id="no-es-uuid",  # type: ignore[arg-type]
                texto="hola",
            )


class TestEventoRequerimientoAutovalidado:
    def test_detalle_vacio_lanza_dato_invalido(self) -> None:
        # Act & Assert
        with pytest.raises(DatoInvalidoError):
            EventoRequerimiento(
                requerimiento_id=uuid.uuid4(),
                tipo_evento=TipoEventoRequerimiento.COMENTARIO,
                autor_id=uuid.uuid4(),
                detalle="",
            )

    def test_tipo_de_evento_crudo_lanza_type_error(self) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            EventoRequerimiento(
                requerimiento_id=uuid.uuid4(),
                tipo_evento="COMENTARIO",  # type: ignore[arg-type]
                autor_id=uuid.uuid4(),
                detalle="x",
            )

    def test_requerimiento_que_no_es_uuid_lanza_type_error(self) -> None:
        # Act & Assert
        with pytest.raises(TypeError):
            EventoRequerimiento(
                requerimiento_id=str(uuid.uuid4()),  # type: ignore[arg-type]
                tipo_evento=TipoEventoRequerimiento.CREACION,
                autor_id=uuid.uuid4(),
                detalle="x",
            )


class TestExigenciasDelUsuario:
    """Tell, Don't Ask: el propio usuario hace cumplir sus respuestas."""

    def test_exigir_autorizacion_negada_lanza_permiso_denegado(self) -> None:
        # Act & Assert
        with pytest.raises(PermisoDenegadoError):
            un_solicitante().exigir_autorizacion(False, "hacer algo")

    def test_exigir_autorizacion_concedida_no_lanza(self) -> None:
        # Act: no lanza
        un_operador().exigir_autorizacion(True, "hacer algo")

    def test_solo_un_tecnico_activo_puede_recibir_requerimientos(self) -> None:
        # Act: no lanza
        un_tecnico().exigir_que_pueda_recibir_requerimientos()

        # Assert
        for usuario in (un_tecnico(activo=False), un_operador(), un_solicitante()):
            with pytest.raises(TecnicoInvalidoError):
                usuario.exigir_que_pueda_recibir_requerimientos()

    def test_solo_reabre_quien_puede_comentar_ese_ticket(self) -> None:
        # Arrange: ticket asignado a `asignado`; `otro` es técnico pero ajeno
        asignado, otro = un_tecnico(), un_tecnico(email="otro@comunicarlos.com.ar")
        ticket = _ticket_resuelto_por(asignado)

        # Assert
        assert asignado.puede_reabrir(ticket)
        assert un_operador().puede_reabrir(ticket)
        assert not otro.puede_reabrir(ticket)
        assert not un_supervisor().puede_reabrir(ticket)
        assert not un_solicitante().puede_reabrir(ticket)

    def test_reabrir_directo_por_un_tecnico_no_asignado_es_rechazado(self) -> None:
        # Arrange
        asignado, otro = un_tecnico(), un_tecnico(email="otro@comunicarlos.com.ar")
        ticket = _ticket_resuelto_por(asignado)

        # Act & Assert: la vía pública no saltea la regla de reapertura
        with pytest.raises(PermisoDenegadoError):
            ticket.reabrir(otro)
        assert ticket.estado == EstadoRequerimiento.RESUELTO

    def test_reabrir_descarta_la_nota_de_resolucion_anterior(self) -> None:
        # Arrange
        tecnico = un_tecnico()
        ticket = _ticket_resuelto_por(tecnico)
        assert ticket.nota_resolucion == "Se cambió el ONT."

        # Act: el técnico asignado comenta y el ticket se reabre
        ticket.agregar_comentario("Volvió a fallar.", tecnico)

        # Assert
        assert ticket.estado == EstadoRequerimiento.EN_PROGRESO
        assert ticket.nota_resolucion is None

    def test_puede_ver_coincide_con_su_criterio_de_visibilidad(self) -> None:
        # Arrange: un ticket propio del solicitante y uno ajeno
        solicitante = un_solicitante()
        propio = _ticket_resuelto_por(un_tecnico())
        ajeno = DatosIncidente(
            titulo="x",
            descripcion="y",
            servicio=ServicioComunicarlos.TELEVISION,
            urgencia=UrgenciaIncidente.MENOR,
            categoria=CategoriaIncidente.BLOQUEO_SIM,
            pasos_reproduccion="p",
        ).construir_para(solicitante)

        # Assert: consulta individual y listado usan la misma regla
        for usuario in (solicitante, un_operador(), un_tecnico(), un_supervisor()):
            criterio = usuario.criterio_visibilidad()
            for ticket in (propio, ajeno):
                assert usuario.puede_ver(ticket) == criterio.es_satisfecho_por(ticket)
        assert solicitante.puede_ver(ajeno)
        assert not solicitante.puede_ver(propio)

    def test_exigir_supervisable(self) -> None:
        # Act: no lanzan
        un_operador().exigir_supervisable()
        un_tecnico().exigir_supervisable()

        # Assert
        for usuario in (un_solicitante(), un_supervisor()):
            with pytest.raises(RolNoSupervisableError):
                usuario.exigir_supervisable()
