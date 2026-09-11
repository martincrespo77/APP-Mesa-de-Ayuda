"""`DespachadorEventos`: Sujeto/Observable del patrón Observer.

Los servicios de aplicación (Paso 3) le entregan cada `EventoRequerimiento`
generado por una transición de estado; el despachador lo reenvía a todos
los observadores suscriptos sin saber qué hace cada uno (loggear, enviar
un email, empujar una notificación push, etc.).
"""

from app.notificaciones.observador import ObservadorRequerimiento
from app.requerimientos.eventos import EventoRequerimiento


class DespachadorEventos:
    """Registra observadores y les notifica cada evento de requerimiento."""

    def __init__(self) -> None:
        self._observadores: list[ObservadorRequerimiento] = []

    def suscribir(self, observador: ObservadorRequerimiento) -> None:
        """Agrega un observador, evitando duplicados."""
        if observador not in self._observadores:
            self._observadores.append(observador)

    def desuscribir(self, observador: ObservadorRequerimiento) -> None:
        """Remueve un observador si estaba suscripto."""
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, evento: EventoRequerimiento) -> None:
        """Reenvía el evento a todos los observadores suscriptos."""
        for observador in self._observadores:
            observador.actualizar(evento)
