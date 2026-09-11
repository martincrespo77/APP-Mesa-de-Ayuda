# 03. Modularidad y Separación de Entidades en Archivos

Una de las directivas fundamentales de la materia es la **separación física de entidades en módulos individuales**. Un proyecto profesional en Python no aglutina todas sus clases en un único archivo.

---

## Regla de Oro: Una Entidad por Archivo

Cada clase que represente una entidad de dominio o componente significativo debe tener su propio archivo `.py`.

### Comparación Estructural

```
❌ ESTRUCTURA MONOLÍTICA (A EVITAR)
sistema/
└── models.py  <-- 1500 líneas con Perro, Gato, Refugio, Adoptante, Pago, etc.

✅ ESTRUCTURA MODULAR COHESIVA (ESTÁNDAR DEL CURSO)
refugio/
├── adopcion/
│   ├── __init__.py
│   ├── estrategia_comun.py
│   ├── estrategia_novato.py
│   └── estrategia_transito.py
├── adoptantes/
│   ├── __init__.py
│   └── adoptante.py
├── rescatados/
│   ├── __init__.py
│   ├── ave.py
│   ├── gato.py
│   ├── mascota.py
│   └── perro.py
├── refugio/
│   ├── __init__.py
│   └── refugio.py
└── main.py
```

---

## Buenas Prácticas de Importación

### 1. Imports Relativos dentro del mismo paquete
Cuando dos entidades pertenecen al mismo subsistema (subpaquete):

```python
# Archivo: refugio/rescatados/perro.py
from .mascota import Mascota  # Import relativo dentro del paquete rescatados
```

### 2. Imports Absolutos entre distintos paquetes
Cuando un módulo requiere una entidad de otro subsistema:

```python
# Archivo: refugio/adopcion/estrategia_comun.py
from refugio.rescatados.mascota import Mascota
```

### 3. Exposición Limpia mediante `__init__.py`
El archivo `__init__.py` puede exponer las clases clave del paquete para simplificar las importaciones externas sin romper la separación física:

```python
# Archivo: refugio/rescatados/__init__.py
from .mascota import Mascota
from .perro import Perro
from .gato import Gato
from .ave import Ave

__all__ = ["Mascota", "Perro", "Gato", "Ave"]
```

---

## Prevención de Dependencias Circulares

Cuando la Entidad A necesita referenciar a la Entidad B y viceversa, la separación de archivos expone el acoplamiento circular.

### Solución: Type Hinting Seguro con `typing.TYPE_CHECKING`

```python
# Archivo: tienda/producto.py
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from tienda.usuario import Usuario

class Producto:
    def precio_para(self, usuario: Optional["Usuario"]) -> float:
        # En tiempo de ejecución no se ejecuta el import cíclico
        if usuario and usuario.es_vip:
            return self.precio_base * 0.8
        return self.precio_base
```

---

## Antipatrones a Evitar

1. **God File / Monster Module**: Archivos con nombres genéricos como `clases.py` o `entidades.py` donde conviven clases sin relación directa.
2. **Importación con Asterisco (`from modulo import *`)**: Oculta el origen de los símbolos, contamina el espacio de nombres y dificulta el análisis estático.
3. **Lógica de Ejecución en Archivos de Entidades**: Los archivos que definen clases NO deben ejecutar código al nivel global del módulo (solo definiciones y métodos). La ejecución pertenece a `main.py` o tests.

---

## Directivas para Agentes de IA

- **Crear un archivo nuevo para cada clase**: Cuando diseñe una solución con 3 entidades (ej. `Orden`, `Cliente`, `Item`), genere 3 archivos correspondientes más el punto de entrada.
- **Mantener alta cohesión**: Cada archivo debe contener únicamente la clase y las funciones auxiliares estrictamente privadas de esa entidad.
