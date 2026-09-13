"""Servicio de aplicación: casos de uso del módulo de supervisión."""

import uuid

from app.compartido.dominio import RolUsuario
from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import RelacionYaExisteError, RolNoSupervisableError
from app.supervision.repositorio import RepositorioSupervision
from app.usuarios.excepciones import UsuarioNoEncontradoError
from app.usuarios.repositorio import RepositorioUsuarios

_ROLES_SUPERVISABLES = frozenset({RolUsuario.OPERADOR, RolUsuario.TECNICO})


class ServicioSupervision:
    """Orquesta el alta, baja y consulta de `RelacionSupervision`."""

    def __init__(
        self, repositorio: RepositorioSupervision, repositorio_usuarios: RepositorioUsuarios
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_usuarios = repositorio_usuarios

    def asignar(
        self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID
    ) -> RelacionSupervision:
        """Crea la relación, exigiendo que el supervisado exista y sea Operador/Técnico."""
        supervisado = self._repositorio_usuarios.buscar_por_id(supervisado_id)
        if supervisado is None:
            raise UsuarioNoEncontradoError(f"No existe un usuario con id '{supervisado_id}'.")
        if supervisado.rol not in _ROLES_SUPERVISABLES:
            raise RolNoSupervisableError(
                f"El rol '{supervisado.rol.value}' no puede ser supervisado."
            )
        if self._repositorio.existe(supervisor_id, supervisado_id):
            raise RelacionYaExisteError(
                "Ya existe una relación de supervisión entre estos usuarios."
            )
        relacion = RelacionSupervision(supervisor_id=supervisor_id, supervisado_id=supervisado_id)
        self._repositorio.asignar(relacion)
        return relacion

    def remover(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> None:
        self._repositorio.remover(supervisor_id, supervisado_id)

    def listar_supervisados_de(self, supervisor_id: uuid.UUID) -> list[RelacionSupervision]:
        return self._repositorio.listar_supervisados_de(supervisor_id)
