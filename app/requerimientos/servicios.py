"""Servicio de aplicación: casos de uso del módulo de requerimientos.

Punto de integración de los patrones del Paso 2/3: pide a la
`FabricaRequerimientos` (Factory Method) que construya la entidad, delega
en `Requerimiento` y en el `Usuario` actor (Information Expert + double
dispatch) toda decisión de negocio, persiste vía `RepositorioRequerimientos`
(Dependency Inversion) y despacha cada `EventoRequerimiento` resultante a
través de `DespachadorEventos` (Observer).

El servicio solo orquesta: recupera las entidades, las opera, persiste y
notifica. No contiene ningún `if` sobre el rol, el estado o los ids de una
entidad: si la operación es inválida, la excepción de dominio se propaga
tal cual. Lo único que valida es la EXISTENCIA de lo que busca en el
repositorio, algo que ninguna entidad puede saber.
"""

import uuid
from collections.abc import Callable
from typing import Any

from app.notificaciones.despachador import DespachadorEventos
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento
from app.requerimientos.excepciones import (
    RequerimientoNoEncontradoError,
    TecnicoInvalidoError,
)
from app.requerimientos.fabrica import FabricaRequerimientos
from app.requerimientos.repositorio import RepositorioRequerimientos
from app.usuarios.dominio import Usuario
from app.usuarios.repositorio import RepositorioUsuarios


class ServicioRequerimientos:
    """Orquesta la creación, consulta y ciclo de vida de los `Requerimiento`."""

    def __init__(
        self,
        repositorio: RepositorioRequerimientos,
        despachador: DespachadorEventos,
        repositorio_usuarios: RepositorioUsuarios,
    ) -> None:
        self._repositorio = repositorio
        self._despachador = despachador
        self._repositorio_usuarios = repositorio_usuarios

    def crear(self, tipo: TipoRequerimiento, **atributos: Any) -> Requerimiento:
        """Crea un requerimiento (cualquier rol puede crear el propio) y lo persiste."""
        requerimiento = FabricaRequerimientos.crear(tipo, **atributos)
        self._repositorio.guardar(requerimiento)
        for evento_inicial in requerimiento.historial:
            self._despachador.notificar(evento_inicial)
        return requerimiento

    def obtener_por_id(self, requerimiento_id: uuid.UUID) -> Requerimiento | None:
        return self._repositorio.buscar_por_id(requerimiento_id)

    def obtener_visible_para(self, requerimiento_id: uuid.UUID, actor: Usuario) -> Requerimiento:
        """Busca un requerimiento y le pide que verifique si `actor` puede verlo."""
        requerimiento = self._buscar_o_lanzar(requerimiento_id)
        requerimiento.exigir_visible_para(actor)
        return requerimiento

    def listar_visibles_para(self, actor: Usuario) -> list[Requerimiento]:
        """Los requerimientos que `actor` puede ver: cada rol elige la consulta."""
        return actor.requerimientos_visibles(self._repositorio)

    def iniciar_analisis(self, requerimiento_id: uuid.UUID, actor: Usuario) -> Requerimiento:
        return self._aplicar_transicion(requerimiento_id, lambda req: req.iniciar_analisis(actor))

    def asignar_tecnico(
        self, requerimiento_id: uuid.UUID, tecnico_id: uuid.UUID, actor: Usuario
    ) -> Requerimiento:
        tecnico = self._buscar_tecnico_o_lanzar(tecnico_id)
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.asignar_tecnico(tecnico, actor)
        )

    def iniciar_progreso(self, requerimiento_id: uuid.UUID, actor: Usuario) -> Requerimiento:
        return self._aplicar_transicion(requerimiento_id, lambda req: req.iniciar_progreso(actor))

    def resolver(
        self, requerimiento_id: uuid.UUID, nota_resolucion: str, actor: Usuario
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.resolver(nota_resolucion, actor)
        )

    def cerrar(self, requerimiento_id: uuid.UUID, actor: Usuario) -> Requerimiento:
        return self._aplicar_transicion(requerimiento_id, lambda req: req.cerrar(actor))

    def cancelar(self, requerimiento_id: uuid.UUID, actor: Usuario) -> Requerimiento:
        return self._aplicar_transicion(requerimiento_id, lambda req: req.cancelar(actor))

    def agregar_comentario(
        self, requerimiento_id: uuid.UUID, texto: str, actor: Usuario
    ) -> Comentario:
        """Agrega el comentario y despacha el/los eventos que haya generado.

        `agregar_comentario` de la entidad puede registrar UN evento
        (`COMENTARIO`) o DOS (`COMENTARIO` + `REAPERTURA`, si reabre un
        `RESUELTO`): se despachan todos los eventos nuevos del historial,
        no solo el último.
        """
        requerimiento = self._buscar_o_lanzar(requerimiento_id)
        cantidad_previa = len(requerimiento.historial)
        comentario = requerimiento.agregar_comentario(texto, actor)
        self._repositorio.guardar(requerimiento)
        for evento_nuevo in requerimiento.historial[cantidad_previa:]:
            self._despachador.notificar(evento_nuevo)
        return comentario

    def derivar_interconsulta(
        self, requerimiento_id: uuid.UUID, tecnico_destino_id: uuid.UUID, actor: Usuario
    ) -> Requerimiento:
        tecnico_destino = self._buscar_tecnico_o_lanzar(tecnico_destino_id)
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.derivar_interconsulta(tecnico_destino, actor)
        )

    def _buscar_tecnico_o_lanzar(self, tecnico_id: uuid.UUID) -> Usuario:
        """Recupera el usuario destino de una asignación/derivación.

        Solo valida que exista: si es o no un Técnico activo lo decide el
        propio `Requerimiento` preguntándole `puede_recibir_requerimientos()`.
        """
        tecnico = self._repositorio_usuarios.buscar_por_id(tecnico_id)
        if tecnico is None:
            raise TecnicoInvalidoError(f"No existe un usuario con id '{tecnico_id}'.")
        return tecnico

    def _buscar_o_lanzar(self, requerimiento_id: uuid.UUID) -> Requerimiento:
        requerimiento = self._repositorio.buscar_por_id(requerimiento_id)
        if requerimiento is None:
            raise RequerimientoNoEncontradoError(
                f"No existe un requerimiento con id '{requerimiento_id}'."
            )
        return requerimiento

    def _aplicar_transicion(
        self,
        requerimiento_id: uuid.UUID,
        transicion: Callable[[Requerimiento], EventoRequerimiento],
    ) -> Requerimiento:
        """Busca el requerimiento, ejecuta la transición, persiste y propaga su evento."""
        requerimiento = self._buscar_o_lanzar(requerimiento_id)
        evento = transicion(requerimiento)
        self._repositorio.guardar(requerimiento)
        self._despachador.notificar(evento)
        return requerimiento
