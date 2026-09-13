"""Adaptador PyMongo de `RepositorioRequerimientos` (Paso 5).

Traduce entre la jerarquía polimórfica `Incidente`/`Solicitud` y documentos
BSON de la colección `requerimientos`, usando el propio discriminador de
dominio (`TipoRequerimiento`) como campo `tipo` en Mongo. La reconstrucción
usa `Incidente.reconstruir`/`Solicitud.reconstruir` (no el constructor
normal): así no se dispara un evento `CREACION` espurio y se restauran
`estado`, `tecnico_asignado_id`, `nota_resolucion` y el historial reales.

El historial de eventos va embebido como subdocumento dentro del mismo
documento de requerimiento (no en una colección `eventos` aparte): hoy no
existe ningún caso de uso que lea eventos de forma independiente, así que
se prioriza la escritura/lectura atómica del agregado completo.

Mapeo polimórfico: un diccionario `TipoRequerimiento -> función` por
dirección (serializar/deserializar), simétrico al catálogo que ya usa
`FabricaRequerimientos` — sin una jerarquía `DbSchema` paralela.
"""

import uuid
from collections.abc import Callable
from typing import Any, cast

from pymongo.collection import Collection
from pymongo.database import Database

from app.compartido.dominio import ServicioComunicarlos
from app.infraestructura.database import COLECCION_REQUERIMIENTOS
from app.requerimientos.dominio.base import Requerimiento
from app.requerimientos.dominio.comentario import Comentario
from app.requerimientos.dominio.estados import EstadoRequerimiento, TipoRequerimiento
from app.requerimientos.dominio.incidente import CategoriaIncidente, Incidente, UrgenciaIncidente
from app.requerimientos.dominio.solicitud import CategoriaSolicitud, Solicitud
from app.requerimientos.eventos import EventoRequerimiento, TipoEventoRequerimiento
from app.requerimientos.repositorio import RepositorioRequerimientos


class RepositorioRequerimientosMongo(RepositorioRequerimientos):
    """Implementación con PyMongo del contrato `RepositorioRequerimientos`."""

    def __init__(self, db: Database[dict[str, Any]]) -> None:
        self._coleccion: Collection[dict[str, Any]] = db[COLECCION_REQUERIMIENTOS]

    def guardar(self, requerimiento: Requerimiento) -> None:
        documento = _a_documento(requerimiento)
        self._coleccion.replace_one({"_id": documento["_id"]}, documento, upsert=True)

    def buscar_por_id(self, requerimiento_id: uuid.UUID) -> Requerimiento | None:
        documento = self._coleccion.find_one({"_id": str(requerimiento_id)})
        return _a_dominio(documento) if documento is not None else None

    def listar_todos(self) -> list[Requerimiento]:
        return [_a_dominio(documento) for documento in self._coleccion.find()]

    def listar_por_solicitante(self, solicitante_id: uuid.UUID) -> list[Requerimiento]:
        filtro = {"solicitante_id": str(solicitante_id)}
        return [_a_dominio(documento) for documento in self._coleccion.find(filtro)]


# -- Eventos de auditoría (subdocumento embebido) -----------------------------


def _evento_a_documento(evento: EventoRequerimiento) -> dict[str, Any]:
    return {
        "id": str(evento.id),
        "tipo_evento": evento.tipo_evento.value,
        "autor_id": str(evento.autor_id),
        "detalle": evento.detalle,
        "timestamp": evento.timestamp,
    }


def _documento_a_evento(
    requerimiento_id: uuid.UUID, documento: dict[str, Any]
) -> EventoRequerimiento:
    return EventoRequerimiento(
        id=uuid.UUID(documento["id"]),
        requerimiento_id=requerimiento_id,
        tipo_evento=TipoEventoRequerimiento(documento["tipo_evento"]),
        autor_id=uuid.UUID(documento["autor_id"]),
        detalle=documento["detalle"],
        timestamp=documento["timestamp"],
    )


# -- Comentarios (subdocumento embebido, igual que el historial) --------------


def _comentario_a_documento(comentario: Comentario) -> dict[str, Any]:
    return {
        "id": str(comentario.id),
        "autor_id": str(comentario.autor_id),
        "texto": comentario.texto,
        "timestamp": comentario.timestamp,
    }


def _documento_a_comentario(
    requerimiento_id: uuid.UUID, documento: dict[str, Any]
) -> Comentario:
    return Comentario(
        id=uuid.UUID(documento["id"]),
        requerimiento_id=requerimiento_id,
        autor_id=uuid.UUID(documento["autor_id"]),
        texto=documento["texto"],
        timestamp=documento["timestamp"],
    )


# -- Campos comunes de la jerarquía Requerimiento ------------------------------


def _campos_comunes_a_documento(requerimiento: Requerimiento) -> dict[str, Any]:
    return {
        "_id": str(requerimiento.id),
        "titulo": requerimiento.titulo,
        "descripcion": requerimiento.descripcion,
        "solicitante_id": str(requerimiento.solicitante_id),
        "estado": requerimiento.estado.value,
        "fecha_creacion": requerimiento.fecha_creacion,
        "tecnico_asignado_id": (
            str(requerimiento.tecnico_asignado_id)
            if requerimiento.tecnico_asignado_id is not None
            else None
        ),
        "nota_resolucion": requerimiento.nota_resolucion,
        "historial": [_evento_a_documento(evento) for evento in requerimiento.historial],
        "comentarios": [
            _comentario_a_documento(comentario) for comentario in requerimiento.comentarios
        ],
    }


def _campos_comunes_desde_documento(documento: dict[str, Any]) -> dict[str, Any]:
    requerimiento_id = uuid.UUID(documento["_id"])
    tecnico_asignado_id = documento["tecnico_asignado_id"]
    return {
        "id": requerimiento_id,
        "titulo": documento["titulo"],
        "descripcion": documento["descripcion"],
        "solicitante_id": uuid.UUID(documento["solicitante_id"]),
        "estado": EstadoRequerimiento(documento["estado"]),
        "fecha_creacion": documento["fecha_creacion"],
        "tecnico_asignado_id": (
            uuid.UUID(tecnico_asignado_id) if tecnico_asignado_id is not None else None
        ),
        "nota_resolucion": documento["nota_resolucion"],
        "historial": [
            _documento_a_evento(requerimiento_id, evento_doc)
            for evento_doc in documento["historial"]
        ],
        "comentarios": [
            _documento_a_comentario(requerimiento_id, comentario_doc)
            for comentario_doc in documento.get("comentarios", [])
        ],
    }


# -- Mapeo polimórfico: tipo -> función serializadora/deserializadora ---------


def _incidente_a_documento(requerimiento: Requerimiento) -> dict[str, Any]:
    incidente = cast(Incidente, requerimiento)
    documento = _campos_comunes_a_documento(incidente)
    documento.update(
        tipo=TipoRequerimiento.INCIDENTE.value,
        urgencia=incidente.urgencia.value,
        categoria=incidente.categoria.value,
        servicio=incidente.servicio.value,
        pasos_reproduccion=incidente.pasos_reproduccion,
    )
    return documento


def _solicitud_a_documento(requerimiento: Requerimiento) -> dict[str, Any]:
    solicitud = cast(Solicitud, requerimiento)
    documento = _campos_comunes_a_documento(solicitud)
    documento.update(
        tipo=TipoRequerimiento.SOLICITUD.value,
        categoria=solicitud.categoria.value,
        servicio=solicitud.servicio.value,
    )
    return documento


def _documento_a_incidente(documento: dict[str, Any]) -> Requerimiento:
    return Incidente.reconstruir(
        **_campos_comunes_desde_documento(documento),
        urgencia=UrgenciaIncidente(documento["urgencia"]),
        categoria=CategoriaIncidente(documento["categoria"]),
        servicio=ServicioComunicarlos(documento["servicio"]),
        pasos_reproduccion=documento["pasos_reproduccion"],
    )


def _documento_a_solicitud(documento: dict[str, Any]) -> Requerimiento:
    return Solicitud.reconstruir(
        **_campos_comunes_desde_documento(documento),
        categoria=CategoriaSolicitud(documento["categoria"]),
        servicio=ServicioComunicarlos(documento["servicio"]),
    )


_SERIALIZADORES: dict[TipoRequerimiento, Callable[[Requerimiento], dict[str, Any]]] = {
    TipoRequerimiento.INCIDENTE: _incidente_a_documento,
    TipoRequerimiento.SOLICITUD: _solicitud_a_documento,
}

_DESERIALIZADORES: dict[TipoRequerimiento, Callable[[dict[str, Any]], Requerimiento]] = {
    TipoRequerimiento.INCIDENTE: _documento_a_incidente,
    TipoRequerimiento.SOLICITUD: _documento_a_solicitud,
}


def _a_documento(requerimiento: Requerimiento) -> dict[str, Any]:
    return _SERIALIZADORES[requerimiento.tipo](requerimiento)


def _a_dominio(documento: dict[str, Any]) -> Requerimiento:
    tipo = TipoRequerimiento(documento["tipo"])
    return _DESERIALIZADORES[tipo](documento)
