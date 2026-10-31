"""Entidad concreta `Tecnico`: resuelve los tickets que tiene asignados.

Todo su poder depende de ser el técnico asignado: solo sobre esos tickets
inicia progreso, resuelve, comenta y deriva. Es el único rol que puede
recibir un ticket, y solo mientras su cuenta está activa.
"""

from typing import TYPE_CHECKING

from app.compartido.dominio import RolUsuario
from app.usuarios.dominio.empleado import Empleado

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento


class Tecnico(Empleado):
    """Empleado técnico: trabaja y resuelve los tickets que le asignan."""

    @property
    def rol(self) -> RolUsuario:
        return RolUsuario.TECNICO

    def puede_iniciar_progreso(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.esta_asignado_a(self)

    def puede_resolver(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.esta_asignado_a(self)

    def puede_comentar(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.esta_asignado_a(self)

    def reabre_al_comentar(self) -> bool:
        return True

    def puede_derivar(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.esta_asignado_a(self)

    def puede_recibir_requerimientos(self) -> bool:
        return self.activo

    def es_supervisable(self) -> bool:
        return True
