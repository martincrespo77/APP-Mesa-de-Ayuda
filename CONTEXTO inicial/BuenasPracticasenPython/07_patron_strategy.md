# 07. Patrón de Comportamiento: Strategy

El patrón **Strategy** define una familia de algoritmos, encapsula cada uno en una clase independiente y los hace intercambiables en tiempo de ejecución. Permite que el algoritmo varíe sin afectar a los clientes que lo utilizan.

---

## Estructura Modular del Patrón

```
pagos/
├── __init__.py
├── base.py                   # Interfaz EstrategiaPago
├── pago_tarjeta.py           # Estrategia concreta PagoTarjeta
├── pago_efectivo.py          # Estrategia concreta PagoEfectivo
└── procesador_pagos.py       # Contexto ProcesadorPagos
```

---

## Código de Implementación

### Archivo: `pagos/base.py`
```python
from abc import ABC, abstractmethod

class EstrategiaPago(ABC):
    """Interfaz abstracta común para todos los algoritmos de pago."""
    @abstractmethod
    def procesar_pago(self, monto: float) -> str:
        pass
```

### Archivo: `pagos/pago_tarjeta.py`
```python
from .base import EstrategiaPago

class PagoTarjeta(EstrategiaPago):
    def procesar_pago(self, monto: float) -> str:
        return f"Procesando ${monto:.2f} con Tarjeta de Crédito 💳"
```

### Archivo: `pagos/pago_efectivo.py`
```python
from .base import EstrategiaPago

class PagoEfectivo(EstrategiaPago):
    def procesar_pago(self, monto: float) -> str:
        return f"Procesando ${monto:.2f} en Efectivo con descuento 💵"
```

### Archivo: `pagos/procesador_pagos.py`
```python
from .base import EstrategiaPago

class ProcesadorPagos:
    """Contexto que delega el algoritmo de cobro en la estrategia inyectada."""
    def __init__(self, estrategia: EstrategiaPago):
        self._estrategia = estrategia

    def cambiar_estrategia(self, nueva_estrategia: EstrategiaPago) -> None:
        """Permite intercambiar el comportamiento en caliente."""
        self._estrategia = nueva_estrategia

    def ejecutar_pago(self, monto: float) -> str:
        if monto <= 0:
            raise ValueError("El monto a pagar debe ser mayor a cero.")
        return self._estrategia.procesar_pago(monto)
```

### Archivo: `main.py`
```python
from pagos.procesador_pagos import ProcesadorPagos
from pagos.pago_tarjeta import PagoTarjeta
from pagos.pago_efectivo import PagoEfectivo

def main():
    # Inicialización con estrategia de tarjeta
    procesador = ProcesadorPagos(PagoTarjeta())
    print(procesador.ejecutar_pago(1500.0))

    # Cambio dinámico a efectivo sin recrear el procesador
    procesador.cambiar_estrategia(PagoEfectivo())
    print(procesador.ejecutar_pago(500.0))

if __name__ == "__main__":
    main()
```

---

## Aplicación en el Caso del Refugio de Mascotas

En el caso del Refugio (Reunión 3 y 5), la política de adopción de cada persona se modeló mediante el patrón Strategy:
- `EstrategiaNovato`: Máximo 1 mascota en total.
- `EstrategiaTransito`: Múltiples mascotas pero todas del mismo tipo.
- `EstrategiaComun`: Múltiples mascotas de cualquier tipo, limitadas por el cupo de cada animal.

La clase `Adoptante` no tiene sentencias `if/else` condicionales para saber qué tipo de adoptante es; simplemente invoca `self.estrategia.puede_adoptar(self, mascota)`.

---

## Directivas para Agentes de IA

1. **Evitar Flags de Tipo**: Nunca implemente atributos como `tipo_pago = "tarjeta"` con ramas `if/elif`. Cree una estrategia para cada variante.
2. **Inyección por Dependencia**: Pase la estrategia en el constructor del contexto para garantizar que el objeto siempre esté listo para operar.
3. **Cada Estrategia en su Archivo**: Mantenga la implementación de cada algoritmo en un módulo `.py` propio.
