"""Tests de dominio del módulo `app/supervision/` (entidad `RelacionSupervision`).

QUIÉN puede supervisar a quién se prueba en `test_usuarios_dominio.py::TestSupervisor`.
"""

import uuid

import pytest

from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import RelacionInvalidaError


class TestRelacionSupervision:
    def test_relacion_valida_nace_con_id_y_fecha_generados(self) -> None:
        # Act
        relacion = RelacionSupervision(supervisor_id=uuid.uuid4(), supervisado_id=uuid.uuid4())

        # Assert
        assert isinstance(relacion.id, uuid.UUID)
        assert relacion.fecha_asignacion is not None

    def test_autosupervision_lanza_error(self) -> None:
        # Arrange
        mismo_id = uuid.uuid4()

        # Act & Assert
        with pytest.raises(RelacionInvalidaError):
            RelacionSupervision(supervisor_id=mismo_id, supervisado_id=mismo_id)

    def test_sabe_a_quien_audita(self) -> None:
        # Arrange
        supervisado_id = uuid.uuid4()
        relacion = RelacionSupervision(supervisor_id=uuid.uuid4(), supervisado_id=supervisado_id)

        # Assert
        assert relacion.audita_a(supervisado_id)
        assert not relacion.audita_a(uuid.uuid4())

    def test_notificar_genera_el_aviso_para_su_supervisor(self) -> None:
        # Arrange
        supervisor_id, supervisado_id = uuid.uuid4(), uuid.uuid4()
        relacion = RelacionSupervision(supervisor_id=supervisor_id, supervisado_id=supervisado_id)
        evento = _evento_de(supervisado_id)

        # Act
        notificacion = relacion.notificar(evento)

        # Assert
        assert notificacion.supervisor_id == supervisor_id
        assert notificacion.empleado_supervisado_id == supervisado_id
        assert notificacion.requerimiento_id == evento.requerimiento_id
        assert notificacion.tipo_evento == evento.tipo_evento
        assert notificacion.leida is False

    def test_no_notifica_eventos_de_un_empleado_que_no_audita(self) -> None:
        # Arrange
        relacion = RelacionSupervision(supervisor_id=uuid.uuid4(), supervisado_id=uuid.uuid4())

        # Act & Assert
        with pytest.raises(RelacionInvalidaError):
            relacion.notificar(_evento_de(uuid.uuid4()))


def _evento_de(autor_id: uuid.UUID) -> EventoRequerimiento:
    return EventoRequerimiento(
        requerimiento_id=uuid.uuid4(),
        tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
        autor_id=autor_id,
        detalle="Estado cambiado.",
    )
