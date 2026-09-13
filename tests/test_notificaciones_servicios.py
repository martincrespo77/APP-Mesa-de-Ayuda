"""Tests de servicios del módulo `app/notificaciones/` (con Fakes en memoria)."""

import uuid

import pytest

from app.notificaciones.dominio import Notificacion
from app.notificaciones.excepciones import NotificacionNoEncontradaError
from app.notificaciones.servicios import ServicioNotificaciones
from app.requerimientos.eventos import TipoEventoRequerimiento
from tests.fakes import FakeRepositorioNotificaciones


@pytest.fixture
def repositorio() -> FakeRepositorioNotificaciones:
    return FakeRepositorioNotificaciones()


@pytest.fixture
def servicio(repositorio: FakeRepositorioNotificaciones) -> ServicioNotificaciones:
    return ServicioNotificaciones(repositorio)


def _crear_notificacion(supervisor_id: uuid.UUID) -> Notificacion:
    return Notificacion(
        supervisor_id=supervisor_id,
        empleado_supervisado_id=uuid.uuid4(),
        requerimiento_id=uuid.uuid4(),
        tipo_evento=TipoEventoRequerimiento.CAMBIO_ESTADO,
        detalle="Cambió de estado.",
    )


class TestListarMias:
    def test_lista_solo_las_del_supervisor(
        self, servicio: ServicioNotificaciones, repositorio: FakeRepositorioNotificaciones
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        mia = _crear_notificacion(supervisor_id)
        ajena = _crear_notificacion(uuid.uuid4())
        repositorio.guardar(mia)
        repositorio.guardar(ajena)

        # Act
        mias = servicio.listar_mias(supervisor_id)

        # Assert
        assert [n.id for n in mias] == [mia.id]


class TestMarcarLeida:
    def test_marcar_leida_persiste_el_cambio(
        self, servicio: ServicioNotificaciones, repositorio: FakeRepositorioNotificaciones
    ) -> None:
        # Arrange
        supervisor_id = uuid.uuid4()
        notificacion = _crear_notificacion(supervisor_id)
        repositorio.guardar(notificacion)

        # Act
        resultado = servicio.marcar_leida(notificacion.id, supervisor_id)

        # Assert
        assert resultado.leida is True
        assert repositorio.buscar_por_id(notificacion.id).leida is True  # type: ignore[union-attr]

    def test_marcar_leida_inexistente_lanza_error(
        self, servicio: ServicioNotificaciones
    ) -> None:
        # Act & Assert
        with pytest.raises(NotificacionNoEncontradaError):
            servicio.marcar_leida(uuid.uuid4(), uuid.uuid4())

    def test_marcar_leida_de_otro_supervisor_lanza_error(
        self, servicio: ServicioNotificaciones, repositorio: FakeRepositorioNotificaciones
    ) -> None:
        # Arrange
        notificacion = _crear_notificacion(uuid.uuid4())
        repositorio.guardar(notificacion)

        # Act & Assert
        with pytest.raises(NotificacionNoEncontradaError):
            servicio.marcar_leida(notificacion.id, uuid.uuid4())
