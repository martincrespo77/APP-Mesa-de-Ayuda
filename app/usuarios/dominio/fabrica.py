"""Factory Method: creación polimórfica de `Usuario` según su rol.

Mismo patrón que `FabricaRequerimientos`: el `RolUsuario` llega como dato
(DTO de alta, documento de Mongo, cambio de rol) y la fábrica lo traduce a
la subclase concreta. Es el ÚNICO lugar del sistema que mapea un valor de
rol a comportamiento; de acá en adelante nadie vuelve a preguntar el rol.
"""

from typing import Any

from app.compartido.dominio import RolUsuario
from app.compartido.validaciones import instancia_de
from app.usuarios.dominio.operador import Operador
from app.usuarios.dominio.solicitante import Solicitante
from app.usuarios.dominio.supervisor import Supervisor
from app.usuarios.dominio.tecnico import Tecnico
from app.usuarios.dominio.usuario import Usuario


class FabricaUsuarios:
    """Fábrica que centraliza la creación de instancias de `Usuario`."""

    _catalogo: dict[RolUsuario, type[Usuario]] = {
        RolUsuario.SOLICITANTE: Solicitante,
        RolUsuario.OPERADOR: Operador,
        RolUsuario.TECNICO: Tecnico,
        RolUsuario.SUPERVISOR: Supervisor,
    }

    @classmethod
    def crear(cls, rol: RolUsuario, **atributos: Any) -> Usuario:
        """Instancia la subclase de `Usuario` correspondiente a `rol`."""
        return cls._catalogo[instancia_de(rol, RolUsuario, "rol")](**atributos)
