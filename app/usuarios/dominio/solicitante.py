"""Entidad concreta `Solicitante`: cliente de la cooperativa que abre tickets.

Solo opera sobre lo propio: ve, comenta y da cierre de conformidad a sus
propios requerimientos, y puede cancelarlos únicamente mientras siguen
ABIERTO. Puede usar cualquier email y debe estar suscripto a al menos un
servicio de la cooperativa.
"""

from typing import TYPE_CHECKING

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.usuarios.dominio.email import Email
from app.usuarios.dominio.usuario import Usuario
from app.usuarios.excepciones import SuscripcionRequeridaError

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.repositorio import RepositorioRequerimientos


class Solicitante(Usuario):
    """Cliente que reporta incidentes y pide altas/bajas sobre sus servicios."""

    @property
    def rol(self) -> RolUsuario:
        return RolUsuario.SOLICITANTE

    def _exigir_email_admitido(self, email: Email) -> None:
        """Regla de negocio: "Los solicitantes utilizarán cualquier correo electrónico"."""

    def _exigir_suscripciones_admitidas(
        self, servicios: frozenset[ServicioComunicarlos]
    ) -> None:
        if not servicios:
            raise SuscripcionRequeridaError(
                "El Solicitante debe estar suscripto a al menos un servicio de la cooperativa."
            )

    def requerimientos_visibles(
        self, repositorio: "RepositorioRequerimientos"
    ) -> list["Requerimiento"]:
        return repositorio.listar_por_solicitante(self.id)

    def puede_ver(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.pertenece_a(self)

    def puede_cerrar(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.pertenece_a(self)

    def puede_cancelar(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.pertenece_a(self) and requerimiento.esta_abierto()

    def puede_comentar(self, requerimiento: "Requerimiento") -> bool:
        return requerimiento.pertenece_a(self)
