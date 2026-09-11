"""Servicio de aplicación: casos de uso del módulo de requerimientos.

Punto de integración de los tres patrones del Paso 2/3: pide a la
`FabricaRequerimientos` (Factory Method) que construya la entidad, delega
en `Requerimiento` (Information Expert) la validación de cada transición,
persiste vía `RepositorioRequerimientos` (Dependency Inversion) y despacha
cada `EventoRequerimiento` resultante a través de `DespachadorEventos`
(Observer). El servicio no repite ninguna validación de negocio ya
resuelta por la entidad: si la transición es inválida, la excepción de
dominio se propaga tal cual.
"""

import uuid
from collections.abc import Callable
from typing import Any

from app.compartido.dominio import RolUsuario
from app.notificaciones.despachador import DespachadorEventos
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.estados import TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento
from app.requerimientos.excepciones import RequerimientoNoEncontradoError
from app.requerimientos.fabrica import FabricaRequerimientos
from app.requerimientos.repositorio import RepositorioRequerimientos


class ServicioRequerimientos:
    """Orquesta la creación, consulta y ciclo de vida de los `Requerimiento`."""

    def __init__(
        self, repositorio: RepositorioRequerimientos, despachador: DespachadorEventos
    ) -> None:
        self._repositorio = repositorio
        self._despachador = despachador

    def crear(self, tipo: TipoRequerimiento, **atributos: Any) -> Requerimiento:
        """Crea un requerimiento (cualquier rol puede crear el propio) y lo persiste."""
        requerimiento = FabricaRequerimientos.crear(tipo, **atributos)
        self._repositorio.guardar(requerimiento)
        for evento_inicial in requerimiento.historial:
            self._despachador.notificar(evento_inicial)
        return requerimiento

    def obtener_por_id(self, requerimiento_id: uuid.UUID) -> Requerimiento | None:
        return self._repositorio.buscar_por_id(requerimiento_id)

    def listar_visibles_para(
        self, rol_actor: RolUsuario, solicitante_id: uuid.UUID
    ) -> list[Requerimiento]:
        """Aplica la visibilidad de la matriz de roles: el Solicitante solo ve lo propio."""
        if rol_actor == RolUsuario.SOLICITANTE:
            return self._repositorio.listar_por_solicitante(solicitante_id)
        return self._repositorio.listar_todos()

    def iniciar_analisis(
        self, requerimiento_id: uuid.UUID, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.iniciar_analisis(autor_id, rol_actor)
        )

    def asignar_tecnico(
        self,
        requerimiento_id: uuid.UUID,
        tecnico_id: uuid.UUID,
        autor_id: uuid.UUID,
        rol_actor: RolUsuario,
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.asignar_tecnico(tecnico_id, autor_id, rol_actor)
        )

    def iniciar_progreso(
        self, requerimiento_id: uuid.UUID, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.iniciar_progreso(autor_id, rol_actor)
        )

    def resolver(
        self,
        requerimiento_id: uuid.UUID,
        nota_resolucion: str,
        autor_id: uuid.UUID,
        rol_actor: RolUsuario,
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.resolver(nota_resolucion, autor_id, rol_actor)
        )

    def cerrar(
        self, requerimiento_id: uuid.UUID, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.cerrar(autor_id, rol_actor)
        )

    def cancelar(
        self, requerimiento_id: uuid.UUID, autor_id: uuid.UUID, rol_actor: RolUsuario
    ) -> Requerimiento:
        return self._aplicar_transicion(
            requerimiento_id, lambda req: req.cancelar(autor_id, rol_actor)
        )

    def _aplicar_transicion(
        self,
        requerimiento_id: uuid.UUID,
        transicion: Callable[[Requerimiento], EventoRequerimiento],
    ) -> Requerimiento:
        """Busca el requerimiento, ejecuta la transición y propaga su evento.

        La transición es responsabilidad exclusiva de la entidad (Information
        Expert): si viola una invariante de estado o de permisos, su propia
        excepción de dominio sube sin que el servicio la intercepte.
        """
        requerimiento = self._repositorio.buscar_por_id(requerimiento_id)
        if requerimiento is None:
            raise RequerimientoNoEncontradoError(
                f"No existe un requerimiento con id '{requerimiento_id}'."
            )
        evento = transicion(requerimiento)
        self._repositorio.guardar(requerimiento)
        self._despachador.notificar(evento)
        return requerimiento
