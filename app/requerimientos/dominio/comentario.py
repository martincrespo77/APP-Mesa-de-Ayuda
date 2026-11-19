"""Value Object `Comentario`: seguimiento inmutable sobre un requerimiento.

Se embebe en el agregado `Requerimiento` (igual que `EventoRequerimiento`),
no en una colección aparte: no hay ningún caso de uso que lea comentarios de
forma independiente de su ticket.

Se autovalida al construirse (`__post_init__`): un `Comentario` sin texto o
con ids que no son `UUID` nunca existe en memoria, venga de
`Requerimiento.agregar_comentario`, de un test o de la reconstrucción desde
Mongo. Quién puede comentar y en qué estado lo sigue decidiendo el ticket.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.compartido.validaciones import instancia_de, texto_obligatorio


@dataclass(frozen=True)
class Comentario:
    """Mensaje de seguimiento agregado por un actor autorizado sobre un ticket."""

    requerimiento_id: uuid.UUID
    autor_id: uuid.UUID
    texto: str
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        instancia_de(self.requerimiento_id, uuid.UUID, "requerimiento_id")
        instancia_de(self.autor_id, uuid.UUID, "autor_id")
        instancia_de(self.id, uuid.UUID, "id")
        instancia_de(self.timestamp, datetime, "timestamp")
        object.__setattr__(self, "texto", texto_obligatorio(self.texto, "texto del comentario"))
