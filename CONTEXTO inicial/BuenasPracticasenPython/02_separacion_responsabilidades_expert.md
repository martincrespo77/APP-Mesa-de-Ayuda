# 02. Asignación de Responsabilidades y Patrón Information Expert

Uno de los principios de diseño más importantes en POO es asignar la responsabilidad de una operación a la clase que posee la información necesaria para cumplirla (**Information Expert** - GRASP).

---

## El Principio de Inversión de Responsabilidad de Validación

### El Problema Común (Antipatrón)
Hacer que una entidad contenedora o cliente (ej. `Adoptante` o `Refugio`) inspeccione y cuente manualmente los atributos de otros objetos:

```python
# ❌ INCORRECTO: Adoptante inspecciona tipos y decide límites ajenos
class Adoptante:
    def adoptar(self, mascota):
        perros = [m for m in self.mascotas if isinstance(m, Perro)]
        if isinstance(mascota, Perro) and len(perros) >= 3:
            raise Exception("Límite de perros superado")
        self.mascotas.append(mascota)
```
*Problema*: Si se agrega una nueva especie (ej. `Ave`), hay que modificar la clase `Adoptante`. Viola el principio Open/Closed.

### La Solución Correcta (Information Expert)
La clase `Mascota` conoce su propio tipo, su política de convivencia y su límite. Por lo tanto, **la mascota valida si puede convivir**:

```python
# ✅ CORRECTO: La mascota valida su propio límite sobre la colección
def puede_convivir_con(self, mascotas_existentes: list) -> bool:
    mismo_tipo = [m for m in mascotas_existentes if isinstance(m, type(self))]
    return len(mismo_tipo) < self.limite_maximo
```

---

## Implementación Modular en Archivos Separados

### Archivo: `rescatados/mascota.py`
```python
from abc import ABC, abstractmethod
from datetime import datetime

class Mascota(ABC):
    def __init__(self, apodo: str, id_mascota: str, fecha_ingreso: datetime):
        self.apodo = apodo
        self.id_mascota = id_mascota
        self.fecha_ingreso = fecha_ingreso

    @abstractmethod
    def cumplir_maximo(self, mascotas_hogar: list) -> bool:
        """La mascota valida si su propio cupo permite sumarse al hogar."""
        pass

    @abstractmethod
    def esta_rehabilitada(self) -> bool:
        pass
```

### Archivo: `rescatados/perro.py`
```python
from datetime import datetime, timedelta
from .mascota import Mascota

class Perro(Mascota):
    LIMITE_MAXIMO = 3

    def cumplir_maximo(self, mascotas_hogar: list) -> bool:
        cantidad = sum(1 for m in mascotas_hogar if isinstance(m, Perro))
        return cantidad < self.LIMITE_MAXIMO

    def esta_rehabilitada(self) -> bool:
        return (datetime.now() - self.fecha_ingreso) >= timedelta(days=30)
```

### Archivo: `rescatados/gato.py`
```python
from datetime import datetime, timedelta
from .mascota import Mascota

class Gato(Mascota):
    LIMITE_MAXIMO = 5

    def cumplir_maximo(self, mascotas_hogar: list) -> bool:
        cantidad = sum(1 for m in mascotas_hogar if isinstance(m, Gato))
        return cantidad < self.LIMITE_MAXIMO

    def esta_rehabilitada(self) -> bool:
        return (datetime.now() - self.fecha_ingreso) >= timedelta(days=180)
```

### Archivo: `adoptantes/adoptante.py`
```python
from rescatados.mascota import Mascota

class Adoptante:
    def __init__(self, nombre: str, estrategia_adopcion):
        self.nombre = nombre
        self.estrategia = estrategia_adopcion
        self.mascotas = []

    def adoptar(self, mascota: Mascota) -> None:
        if not self.estrategia.puede_adoptar(self, mascota):
            raise ValueError(f"{self.nombre} no cumple las reglas para adoptar a {mascota.apodo}")
        self.mascotas.append(mascota)
```

---

## Reglas para Agentes de IA

1. **Tell, Don't Ask**: No le pida los datos a un objeto para calcular algo por él. Pídale al objeto que haga el cálculo y le devuelva la respuesta.
2. **Encapsular Políticas Específicas**: Si un límite o regla pertenece a una subclase (ej. límite de 3 para perros y 5 para gatos), esa constante y su validación deben residir dentro de esa subclase.
3. **Extensibilidad sin Modificación**: Al incorporar un nuevo animal (ej. `Tortuga`), no se debe tocar una sola línea de código en `Adoptante` ni en `Refugio`.
