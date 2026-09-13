"""Entidad concreta `Incidente`: interrupción o degradación de un servicio."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import cast

from app.compartido.dominio import ServicioComunicarlos
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.eventos import EventoRequerimiento


class UrgenciaIncidente(StrEnum):
    """Nivel de urgencia con el que debe atenderse el incidente."""

    CRITICO = "CRITICO"
    IMPORTANTE = "IMPORTANTE"
    MENOR = "MENOR"


class CategoriaIncidente(StrEnum):
    """Naturaleza del incidente reportado."""

    SERVICIO_INACCESIBLE = "SERVICIO_INACCESIBLE"
    BLOQUEO_SIM = "BLOQUEO_SIM"
    PERDIDA_O_DESTRUCCION_DE_EQUIPO = "PERDIDA_O_DESTRUCCION_DE_EQUIPO"


class Incidente(Requerimiento):
    """Corte o degradación anormal de un servicio existente (fibra, IP, TV)."""

    def __init__(
        self,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        urgencia: UrgenciaIncidente,
        categoria: CategoriaIncidente,
        servicio: ServicioComunicarlos,
        pasos_reproduccion: str,
        id: uuid.UUID | None = None,
    ) -> None:
        super().__init__(titulo, descripcion, solicitante_id, id)
        self.urgencia = self._validar_urgencia(urgencia)
        self.categoria = self._validar_categoria(categoria)
        self.servicio = self._validar_servicio(servicio)
        self.pasos_reproduccion = self._validar_pasos_reproduccion(pasos_reproduccion)

    @property
    def tipo(self) -> TipoRequerimiento:
        return TipoRequerimiento.INCIDENTE

    @classmethod
    def reconstruir(
        cls,
        *,
        id: uuid.UUID,
        titulo: str,
        descripcion: str,
        solicitante_id: uuid.UUID,
        estado: EstadoRequerimiento,
        fecha_creacion: datetime,
        tecnico_asignado_id: uuid.UUID | None,
        nota_resolucion: str | None,
        historial: list[EventoRequerimiento],
        urgencia: UrgenciaIncidente,
        categoria: CategoriaIncidente,
        servicio: ServicioComunicarlos,
        pasos_reproduccion: str,
        comentarios: list[Comentario] | None = None,
    ) -> "Incidente":
        """Reconstruye un `Incidente` ya persistido (uso exclusivo de repositorios)."""
        instancia = cast(
            "Incidente",
            cls._reconstruir_base(
                id=id,
                titulo=titulo,
                descripcion=descripcion,
                solicitante_id=solicitante_id,
                estado=estado,
                fecha_creacion=fecha_creacion,
                tecnico_asignado_id=tecnico_asignado_id,
                nota_resolucion=nota_resolucion,
                historial=historial,
                comentarios=comentarios,
            ),
        )
        instancia.urgencia = urgencia
        instancia.categoria = categoria
        instancia.servicio = servicio
        instancia.pasos_reproduccion = pasos_reproduccion
        return instancia

    @staticmethod
    def _validar_urgencia(urgencia: UrgenciaIncidente) -> UrgenciaIncidente:
        if not isinstance(urgencia, UrgenciaIncidente):
            raise TypeError("La urgencia debe ser una instancia de UrgenciaIncidente.")
        return urgencia

    @staticmethod
    def _validar_categoria(categoria: CategoriaIncidente) -> CategoriaIncidente:
        if not isinstance(categoria, CategoriaIncidente):
            raise TypeError("La categoría debe ser una instancia de CategoriaIncidente.")
        return categoria

    @staticmethod
    def _validar_servicio(servicio: ServicioComunicarlos) -> ServicioComunicarlos:
        if not isinstance(servicio, ServicioComunicarlos):
            raise TypeError("El servicio debe ser una instancia de ServicioComunicarlos.")
        return servicio

    @staticmethod
    def _validar_pasos_reproduccion(pasos_reproduccion: str) -> str:
        if not isinstance(pasos_reproduccion, str):
            raise TypeError("Los pasos de reproducción deben ser una cadena de texto.")
        pasos_normalizados = pasos_reproduccion.strip()
        if not pasos_normalizados:
            raise ValueError("Los pasos de reproducción no pueden estar vacíos.")
        return pasos_normalizados
