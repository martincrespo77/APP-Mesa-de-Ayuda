"""Entidad concreta `Supervisor`: autoridad operativa y auditora.

Puede ejecutar cualquier transición del ciclo de vida (incluso iniciar
progreso o resolver sin ser el técnico asignado), pero no comenta ni
deriva: no participa del seguimiento diario. Es el único que administra
usuarios y supervisiones, y el único que recibe notificaciones de las
acciones de sus supervisados.
"""

from typing import TYPE_CHECKING

from app.compartido.dominio import RolUsuario
from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import RolNoSupervisableError
from app.usuarios.dominio.empleado import Empleado
from app.usuarios.dominio.usuario import Usuario

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento


class Supervisor(Empleado):
    """Empleado jerárquico: control total del ciclo de vida y auditoría."""

    @property
    def rol(self) -> RolUsuario:
        return RolUsuario.SUPERVISOR

    def supervisar(self, empleado: "Usuario") -> RelacionSupervision:
        """Establece una relación de supervisión sobre `empleado`.

        Es el empleado quien sabe si es supervisable (Operador y Técnico sí;
        Solicitante y Supervisor no): el Supervisor le pregunta, no mira su rol.
        """
        if not empleado.es_supervisable():
            raise RolNoSupervisableError(
                f"El rol '{empleado.rol.value}' no puede ser supervisado."
            )
        return RelacionSupervision(supervisor_id=self.id, supervisado_id=empleado.id)

    def puede_iniciar_analisis(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_asignar_tecnico(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_iniciar_progreso(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_resolver(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_cerrar(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_cancelar(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_administrar_usuarios(self) -> bool:
        return True

    def puede_administrar_supervisiones(self) -> bool:
        return True

    def recibe_notificaciones(self) -> bool:
        return True
