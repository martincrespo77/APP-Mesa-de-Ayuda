"""Tests de dominio del módulo `app/supervision/` (entidad `RelacionSupervision`)."""

import uuid

import pytest

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
