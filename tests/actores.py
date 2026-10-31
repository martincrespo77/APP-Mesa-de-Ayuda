"""Helpers de arrange: construcción de usuarios (actores) para los tests.

`Usuario` es abstracta: cada rol es una subclase. `nuevo_usuario` conserva
la firma "datos + rol" que usan los tests de servicios, routers e
infraestructura (que reciben el rol como dato, igual que un DTO o un
documento de Mongo) y delega en `FabricaUsuarios`. Los `un_*` arman un
actor válido de cada rol con datos por defecto, para los tests de dominio.
"""

from typing import Any

from app.compartido.dominio import RolUsuario, ServicioComunicarlos
from app.usuarios.dominio import (
    FabricaUsuarios,
    Operador,
    Solicitante,
    Supervisor,
    Tecnico,
    Usuario,
)

UN_SERVICIO = frozenset({ServicioComunicarlos.INTERNET_BANDA_ANCHA})


def nuevo_usuario(
    nombre_completo: str, email: str, password_hash: str, rol: RolUsuario, **atributos: Any
) -> Usuario:
    """Crea el usuario del `rol` dado vía `FabricaUsuarios` (rol como dato)."""
    return FabricaUsuarios.crear(
        rol,
        nombre_completo=nombre_completo,
        email=email,
        password_hash=password_hash,
        **atributos,
    )


def un_solicitante(email: str = "lucia@gmail.com", **atributos: Any) -> Solicitante:
    atributos.setdefault("servicios_suscriptos", UN_SERVICIO)
    return Solicitante("Lucía Gómez", email, "hash", **atributos)


def un_operador(email: str = "rosa@comunicarlos.com.ar", **atributos: Any) -> Operador:
    return Operador("Rosa Molina", email, "hash", **atributos)


def un_tecnico(email: str = "ivan@comunicarlos.com.ar", **atributos: Any) -> Tecnico:
    return Tecnico("Iván Ríos", email, "hash", **atributos)


def un_supervisor(email: str = "sofia@comunicarlos.com.ar", **atributos: Any) -> Supervisor:
    return Supervisor("Sofía Jefa", email, "hash", **atributos)
