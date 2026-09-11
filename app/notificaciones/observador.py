"""Interfaz `Observador` del patrón Observer para eventos de requerimientos."""

from abc import ABC, abstractmethod

from app.requerimientos.eventos import EventoRequerimiento


class ObservadorRequerimiento(ABC):
    """Contrato que debe implementar todo suscriptor de eventos de requerimientos.

    El dominio de `requerimientos` no conoce esta interfaz ni a sus
    implementaciones (evita el acoplamiento inverso); es `notificaciones`
    quien depende de `requerimientos`, nunca al revés.
    """

    @abstractmethod
    def actualizar(self, evento: EventoRequerimiento) -> None:
        """Reacciona a un `EventoRequerimiento` recién despachado."""
