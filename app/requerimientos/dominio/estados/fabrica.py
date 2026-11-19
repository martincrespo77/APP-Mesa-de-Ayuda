"""Factory Method: hidrata el `EstadoTicket` concreto desde su código persistido.

Es el ÚNICO lugar del sistema que traduce un `EstadoRequerimiento` a su
clase de comportamiento (mismo rol que `FabricaUsuarios` para `RolUsuario`).
Agregar un estado nuevo es crear su clase y registrarla acá.
"""

from app.compartido.validaciones import instancia_de
from app.requerimientos.dominio.codigos import EstadoRequerimiento
from app.requerimientos.dominio.estados.abierto import EstadoAbierto
from app.requerimientos.dominio.estados.base import EstadoTicket
from app.requerimientos.dominio.estados.cancelado import EstadoCancelado
from app.requerimientos.dominio.estados.cerrado import EstadoCerrado
from app.requerimientos.dominio.estados.en_analisis import EstadoEnAnalisis
from app.requerimientos.dominio.estados.en_progreso import EstadoEnProgreso
from app.requerimientos.dominio.estados.resuelto import EstadoResuelto


class FabricaEstados:
    """Traduce códigos de estado (BD, DTOs) a objetos `EstadoTicket`."""

    _catalogo: dict[EstadoRequerimiento, type[EstadoTicket]] = {
        EstadoRequerimiento.ABIERTO: EstadoAbierto,
        EstadoRequerimiento.EN_ANALISIS: EstadoEnAnalisis,
        EstadoRequerimiento.EN_PROGRESO: EstadoEnProgreso,
        EstadoRequerimiento.RESUELTO: EstadoResuelto,
        EstadoRequerimiento.CERRADO: EstadoCerrado,
        EstadoRequerimiento.CANCELADO: EstadoCancelado,
    }

    @classmethod
    def desde_codigo(cls, codigo: EstadoRequerimiento) -> EstadoTicket:
        """Devuelve el objeto estado correspondiente a `codigo` (hidratación desde BD)."""
        return cls._catalogo[instancia_de(codigo, EstadoRequerimiento, "estado")]()

    @classmethod
    def inicial(cls) -> EstadoTicket:
        """Estado con el que nace todo requerimiento nuevo."""
        return EstadoAbierto()
