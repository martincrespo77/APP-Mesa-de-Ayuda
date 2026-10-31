"""Servicio de aplicación: casos de uso del módulo de supervisión."""

import uuid

from app.supervision.dominio import RelacionSupervision
from app.supervision.excepciones import RelacionYaExisteError
from app.supervision.repositorio import RepositorioSupervision
from app.usuarios.dominio import Usuario
from app.usuarios.excepciones import UsuarioNoEncontradoError
from app.usuarios.repositorio import RepositorioUsuarios


class ServicioSupervision:
    """Orquesta el alta, baja y consulta de `RelacionSupervision`."""

    def __init__(
        self, repositorio: RepositorioSupervision, repositorio_usuarios: RepositorioUsuarios
    ) -> None:
        self._repositorio = repositorio
        self._repositorio_usuarios = repositorio_usuarios

    def asignar(self, supervisor: Usuario, supervisado_id: uuid.UUID) -> RelacionSupervision:
        """Le pide a `supervisor` que supervise al usuario indicado.

        Si el supervisado es supervisable lo decide el dominio
        (`Supervisor.supervisar`); el servicio solo valida lo que requiere
        al repositorio: que el supervisado exista y que la relación no
        esté ya registrada.
        """
        supervisado = self._repositorio_usuarios.buscar_por_id(supervisado_id)
        if supervisado is None:
            raise UsuarioNoEncontradoError(f"No existe un usuario con id '{supervisado_id}'.")
        relacion = supervisor.supervisar(supervisado)
        if self._repositorio.existe(supervisor.id, supervisado.id):
            raise RelacionYaExisteError(
                "Ya existe una relación de supervisión entre estos usuarios."
            )
        self._repositorio.asignar(relacion)
        return relacion

    def remover(self, supervisor_id: uuid.UUID, supervisado_id: uuid.UUID) -> None:
        self._repositorio.remover(supervisor_id, supervisado_id)

    def listar_supervisados_de(self, supervisor_id: uuid.UUID) -> list[RelacionSupervision]:
        return self._repositorio.listar_supervisados_de(supervisor_id)
