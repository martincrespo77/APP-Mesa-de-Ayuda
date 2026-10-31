"""Entidad concreta `Incidente`: interrupción o degradación de un servicio."""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import cast

from app.compartido.dominio import ServicioComunicarlos
from app.compartido.validaciones import instancia_de, texto_obligatorio
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
        self.urgencia = instancia_de(urgencia, UrgenciaIncidente, "urgencia")
        self.categoria = instancia_de(categoria, CategoriaIncidente, "categoría")
        self.servicio = instancia_de(servicio, ServicioComunicarlos, "servicio")
        self.pasos_reproduccion = texto_obligatorio(pasos_reproduccion, "pasos de reproducción")

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
