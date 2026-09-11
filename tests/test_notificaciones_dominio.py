"""Tests de dominio del módulo `app/notificaciones/` (patrón Observer)."""

import logging
import uuid

import pytest

from app.notificaciones.despachador import DespachadorEventos
from app.notificaciones.observador import ObservadorRequerimiento
from app.notificaciones.observador_logger import ObservadorLogger
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento


class _ObservadorEspia(ObservadorRequerimiento):
    """Doble de prueba mínimo: registra los eventos recibidos."""

    def __init__(self) -> None:
        self.eventos_recibidos: list[EventoRequerimiento] = []

    def actualizar(self, evento: EventoRequerimiento) -> None:
        self.eventos_recibidos.append(evento)


@pytest.fixture
def evento() -> EventoRequerimiento:
    # Arrange: evento de dominio arbitrario, sin depender de una entidad real
    return EventoRequerimiento(
        requerimiento_id=uuid.uuid4(),
        tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
        autor_id=uuid.uuid4(),
        detalle="Estado cambiado de ABIERTO a EN_ANALISIS.",
    )


class TestDespachadorEventos:
    def test_notificar_llama_actualizar_en_cada_observador_suscripto(
        self, evento: EventoRequerimiento
    ) -> None:
        # Arrange
        despachador = DespachadorEventos()
        espia_1 = _ObservadorEspia()
        espia_2 = _ObservadorEspia()
        despachador.suscribir(espia_1)
        despachador.suscribir(espia_2)

        # Act
        despachador.notificar(evento)

        # Assert
        assert espia_1.eventos_recibidos == [evento]
        assert espia_2.eventos_recibidos == [evento]

    def test_suscribir_el_mismo_observador_dos_veces_no_lo_duplica(
        self, evento: EventoRequerimiento
    ) -> None:
        # Arrange
        despachador = DespachadorEventos()
        espia = _ObservadorEspia()
        despachador.suscribir(espia)
        despachador.suscribir(espia)

        # Act
        despachador.notificar(evento)

        # Assert: si estuviera duplicado, recibiría el evento dos veces
        assert espia.eventos_recibidos == [evento]

    def test_desuscribir_detiene_las_notificaciones_futuras(
        self, evento: EventoRequerimiento
    ) -> None:
        # Arrange
        despachador = DespachadorEventos()
        espia = _ObservadorEspia()
        despachador.suscribir(espia)
        despachador.desuscribir(espia)

        # Act
        despachador.notificar(evento)

        # Assert
        assert espia.eventos_recibidos == []

    def test_notificar_sin_observadores_no_lanza_error(self, evento: EventoRequerimiento) -> None:
        # Arrange
        despachador = DespachadorEventos()

        # Act & Assert: no debe lanzar excepción alguna
        despachador.notificar(evento)


class TestObservadorLogger:
    def test_actualizar_registra_el_evento_en_el_logger_de_auditoria(
        self, evento: EventoRequerimiento, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Arrange
        observador = ObservadorLogger()

        # Act
        with caplog.at_level(logging.INFO, logger="mesa_de_ayuda.auditoria"):
            observador.actualizar(evento)

        # Assert
        assert str(evento.requerimiento_id) in caplog.text
        assert "CAMBIO_ESTADO" in caplog.text
