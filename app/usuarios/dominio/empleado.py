"""Clase abstracta `Empleado`: lo común a Operador, Técnico y Supervisor.

Los tres son personal de la cooperativa, y eso fija dos invariantes que
antes eran `if rol in _ROLES_CON_EMAIL_CORPORATIVO` dentro de `Usuario`:
usan el email corporativo y no son clientes (no tienen servicios
suscriptos). Además, todo empleado ve la bandeja completa de requerimientos
y puede consultar el listado de técnicos (para asignar o derivar).
"""

from abc import ABC
from typing import TYPE_CHECKING

from app.compartido.dominio import ServicioComunicarlos
from app.usuarios.dominio.email import Email
from app.usuarios.dominio.usuario import Usuario
from app.usuarios.excepciones import EmailCorporativoRequeridoError, SuscripcionRequeridaError

if TYPE_CHECKING:
    from app.requerimientos.dominio.base import Requerimiento
    from app.requerimientos.repositorio import RepositorioRequerimientos

DOMINIO_CORPORATIVO = "comunicarlos.com.ar"


class Empleado(Usuario, ABC):
    """Personal de la cooperativa: email corporativo, sin suscripciones, ve todo."""

    def _exigir_email_admitido(self, email: Email) -> None:
        if not email.pertenece_al_dominio(DOMINIO_CORPORATIVO):
            raise EmailCorporativoRequeridoError(
                f"El rol '{self.rol}' requiere un email corporativo "
                f"'@{DOMINIO_CORPORATIVO}' (recibido: '{email}')."
            )

    def _exigir_suscripciones_admitidas(
        self, servicios: frozenset[ServicioComunicarlos]
    ) -> None:
        if servicios:
            raise SuscripcionRequeridaError(
                f"El rol '{self.rol}' no puede tener servicios suscriptos (solo el Solicitante)."
            )

    def requerimientos_visibles(
        self, repositorio: "RepositorioRequerimientos"
    ) -> list["Requerimiento"]:
        return repositorio.listar_todos()

    def puede_ver(self, requerimiento: "Requerimiento") -> bool:
        return True

    def puede_consultar_tecnicos(self) -> bool:
        return True
