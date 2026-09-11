# 09. Patrones Estructurales: Adapter y Decorator

Los patrones estructurales abordan la **composición de clases y objetos** para formar estructuras complejas manteniendo la flexibilidad y la independencia de componentes.

---

## 1. Patrón Adapter: Integración de Interfaces Incompatibles

El patrón **Adapter** actúa como un traductor entre dos sistemas o clases que tienen interfaces incompatibles, permitiendo que colaboren sin modificar el código legacy preexistente.

### Archivo: `pagos/legacy_gateway.py`
```python
class GatewayLegacy:
    """Sistema heredado que trabaja en centavos y con nombres de método arcaicos."""
    def ejecutar_debito_centavos(self, centavos: int) -> str:
        return f"OK_TRANS_CENTAVOS_{centavos}"
```

### Archivo: `pagos/interfaz_moderna.py`
```python
from abc import ABC, abstractmethod

class ProcesadorModerno(ABC):
    """Interfaz estándar esperada por las aplicaciones actuales (en dólares)."""
    @abstractmethod
    def pagar(self, monto_dolares: float) -> str:
        pass
```

### Archivo: `pagos/adapter_gateway.py`
```python
from .interfaz_moderna import ProcesadorModerno
from .legacy_gateway import GatewayLegacy

class AdapterGateway(ProcesadorModerno):
    """Adapta el gateway antiguo a la interfaz moderna esperada."""
    def __init__(self, legacy: GatewayLegacy):
        self._legacy = legacy

    def pagar(self, monto_dolares: float) -> str:
        # Conversión de unidades requerida por el legacy
        centavos = int(monto_dolares * 100)
        respuesta = self._legacy.ejecutar_debito_centavos(centavos)
        return f"Pago adaptado con éxito: ${monto_dolares:.2f} (Ref: {respuesta})"
```

---

## 2. Patrón Decorator: Extensión Dinámica vs Herencia

El patrón **Decorator** permite añadir responsabilidades adicionales a un objeto de manera dinámica. Es la alternativa preferida a la herencia cuando la combinación de subclases generaría una explosión combinatoria (ej. `CafeConLecheYChocolateYCrema`).

### Archivo: `cafeteria/bebida.py`
```python
from abc import ABC, abstractmethod

class Bebida(ABC):
    @abstractmethod
    def costo(self) -> float:
        pass

    @abstractmethod
    def descripcion(self) -> str:
        pass
```

### Archivo: `cafeteria/cafe_simple.py`
```python
from .bebida import Bebida

class CafeSimple(Bebida):
    def costo(self) -> float:
        return 1000.0

    def descripcion(self) -> str:
        return "Café Expreso"
```

### Archivo: `cafeteria/decorador_bebida.py`
```python
from .bebida import Bebida

class DecoradorBebida(Bebida):
    """Decorador base que envuelve a una Bebida y delega sus métodos."""
    def __init__(self, bebida: Bebida):
        self._bebida = bebida

    def costo(self) -> float:
        return self._bebida.costo()

    def descripcion(self) -> str:
        return self._bebida.descripcion()
```

### Archivo: `cafeteria/ingredientes.py`
```python
from .decorador_bebida import DecoradorBebida

class ConLeche(DecoradorBebida):
    def costo(self) -> float:
        return self._bebida.costo() + 250.0

    def descripcion(self) -> str:
        return f"{self._bebida.descripcion()} + Leche"

class ConChocolate(DecoradorBebida):
    def costo(self) -> float:
        return self._bebida.costo() + 400.0

    def descripcion(self) -> str:
        return f"{self._bebida.descripcion()} + Chocolate"
```

### Archivo: `main.py`
```python
from cafeteria.cafe_simple import CafeSimple
from cafeteria.ingredientes import ConLeche, ConChocolate

def main():
    # Composición dinámica en tiempo de ejecución
    pedido = CafeSimple()
    pedido = ConLeche(pedido)
    pedido = ConChocolate(pedido)
    # Doble chocolate
    pedido = ConChocolate(pedido)

    print(f"Pedido: {pedido.descripcion()} | Total: ${pedido.costo():.2f}")

if __name__ == "__main__":
    main()
```

---

## Comparativa y Criterios de Elección

| Patrón | Problema que Resuelve | Relación de Objetos |
|---|---|---|
| **Adapter** | Interfaces incompatibles o código legacy que no podemos modificar. | Envuelve un objeto incompatible para adaptarlo a un contrato nuevo. |
| **Decorator** | Añadir comportamientos dinámicos y combinables sin crear decenas de subclases. | Envuelve un objeto del mismo tipo y extiende su comportamiento de forma recursiva. |

---

## Directivas para Agentes de IA

1. **Evitar Explosión de Subclases**: Ante combinaciones múltiples de características opcionales (toppings, modificadores de precio, middlewares), use **Decorator** en lugar de herencia múltiple.
2. **Respetar la Interfaz Base en Decorator**: Toda clase decoradora debe heredar de la misma clase abstracta que el objeto decorado para mantener la transparencia polimórfica.
