# 06. Patrón Creacional: Factory Method

El patrón **Factory Method** define una interfaz o método de creación de objetos, permitiendo que la lógica de instanciación quede desacoplada del código cliente. Cumple de manera directa con el principio **Open/Closed** (abierto a la extensión, cerrado a la modificación).

---

## Estructura de Entidades en Archivos Separados

```
vehiculos/
├── __init__.py
├── base.py              # Interfaz abstracta Vehiculo
├── auto.py              # Implementación concreta Auto
├── moto.py              # Implementación concreta Moto
└── fabrica.py           # FabricaVehiculos
```

---

## Código de Implementación

### Archivo: `vehiculos/base.py`
```python
from abc import ABC, abstractmethod

class Vehiculo(ABC):
    """Contrato base que deben implementar todos los vehículos."""
    @abstractmethod
    def acelerar(self) -> str:
        pass
```

### Archivo: `vehiculos/auto.py`
```python
from .base import Vehiculo

class Auto(Vehiculo):
    def acelerar(self) -> str:
        return "Auto acelerando sobre 4 ruedas 🚗"
```

### Archivo: `vehiculos/moto.py`
```python
from .base import Vehiculo

class Moto(Vehiculo):
    def acelerar(self) -> str:
        return "Moto acelerando sobre 2 ruedas 🏍️"
```

### Archivo: `vehiculos/fabrica.py`
```python
from typing import Dict, Type
from .base import Vehiculo
from .auto import Auto
from .moto import Moto

class FabricaVehiculos:
    """Fábrica que centraliza la creación de instancias de vehículos."""
    _catalogo: Dict[str, Type[Vehiculo]] = {
        "auto": Auto,
        "moto": Moto,
    }

    @classmethod
    def crear_vehiculo(cls, tipo: str) -> Vehiculo:
        tipo_normalizado = tipo.lower().strip()
        clase_vehiculo = cls._catalogo.get(tipo_normalizado)
        if not clase_vehiculo:
            tipos_validos = ", ".join(cls._catalogo.keys())
            raise ValueError(f"Tipo '{tipo}' no soportado. Disponibles: {tipos_validos}")
        return clase_vehiculo()

    @classmethod
    def registrar_tipo(cls, clave: str, clase_vehiculo: Type[Vehiculo]) -> None:
        """Permite extender la fábrica dinámicamente sin modificar su código base."""
        cls._catalogo[clave.lower().strip()] = clase_vehiculo
```

### Archivo: `main.py`
```python
from vehiculos.fabrica import FabricaVehiculos

def main():
    vehiculo_1 = FabricaVehiculos.crear_vehiculo("auto")
    print(vehiculo_1.acelerar())

    vehiculo_2 = FabricaVehiculos.crear_vehiculo("moto")
    print(vehiculo_2.acelerar())

if __name__ == "__main__":
    main()
```

---

## Beneficios Clave

1. **Desacoplamiento Total**: El cliente solo conoce la interfaz `Vehiculo` y la fábrica. Desconoce las clases concretas `Auto` o `Moto`.
2. **Facilidad de Extensión**: Para añadir `Camion`, solo se crea `vehiculos/camion.py` y se registra en la fábrica sin alterar el resto de la aplicación.
3. **Manejo Centralizado de Errores**: Si se solicita un tipo inexistente, la fábrica rechaza la creación de forma coherente con un `ValueError`.

---

## Directivas para Agentes de IA

- **No usar `if/elif` extensos y rígidos en el cliente**: Utilice un diccionario de registro o mapeo en la fábrica.
- **Retornar siempre la abstracción base**: La firma de retorno debe ser de tipo `Vehiculo` (la interfaz abstracta).
- **Mantener clases concretas en sus propios archivos**.
