"""Observador concreto: genera una `Notificacion` por cada supervisor de un
empleado (Operador/Técnico) que generó un `EventoRequerimiento`.

Vive en `app/infraestructura/` (no en `notificaciones/`), tal como ya
anticipaba el docstring de `observador_logger.py`: necesita repositorios
reales (`RepositorioUsuarios`, `RepositorioSupervision`,
`RepositorioNotificaciones`) construidos sobre el `db` de la request
actual, a diferencia de `ObservadorLogger`, que no depende de nada externo.
Se suscribe al mismo `DespachadorEventos` sin que `requerimientos` sepa que
existe (Observer).
"""

from app.compartido.dominio import RolUsuario
from app.notificaciones.dominio import Notificacion
from app.notificaciones.observador import ObservadorRequerimiento
from app.notificaciones.repositorio import RepositorioNotificaciones
from app.requerimientos.eventos import EventoRequerimiento
from app.supervision.repositorio import RepositorioSupervision
from app.usuarios.repositorio import RepositorioUsuarios

_ROLES_SUPERVISABLES = frozenset({RolUsuario.OPERADOR, RolUsuario.TECNICO})


class ObservadorNotificacionesMongo(ObservadorRequerimiento):
    """Notifica a los supervisores de un empleado cada vez que este genera un evento."""

    def __init__(
        self,
        repositorio_usuarios: RepositorioUsuarios,
        repositorio_supervision: RepositorioSupervision,
        repositorio_notificaciones: RepositorioNotificaciones,
    ) -> None:
        self._repositorio_usuarios = repositorio_usuarios
        self._repositorio_supervision = repositorio_supervision
        self._repositorio_notificaciones = repositorio_notificaciones

    def actualizar(self, evento: EventoRequerimiento) -> None:
        autor = self._repositorio_usuarios.buscar_por_id(evento.autor_id)
        if autor is None or autor.rol not in _ROLES_SUPERVISABLES:
            return
        relaciones = self._repositorio_supervision.listar_supervisores_de(autor.id)
        for relacion in relaciones:
            notificacion = Notificacion(
                supervisor_id=relacion.supervisor_id,
                empleado_supervisado_id=autor.id,
                requerimiento_id=evento.requerimiento_id,
                tipo_evento=evento.tipo_evento,
                detalle=evento.detalle,
            )
            self._repositorio_notificaciones.guardar(notificacion)
