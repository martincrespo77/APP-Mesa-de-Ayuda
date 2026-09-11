# 05. Patrón Creacional: Singleton

El patrón **Singleton** garantiza que una clase tenga únicamente una instancia en todo el ciclo de vida de la aplicación y proporciona un punto de acceso global y consistente a ella.

---

## Propósito y Casos de Uso Válidos

- **Configuración centralizada del sistema**: Parámetros de conexión, variables de entorno, flags de características.
- **Pool de conexiones o clientes externos**: Conexiones a bases de datos o brokers de mensajería donde abrir múltiples instancias es ineficiente o destructivo.
- **Registro de auditoría o logging global**.

---

## Implementación Canónica en Python con `__new__`

En Python, el método de clase `__new__(cls)` es el encargado directo de instanciar el objeto en memoria antes de invocar a `__init__`. Al interceptarlo, podemos reutilizar la misma instancia.

### Archivo: `configuracion/config_sistema.py`
```python
from typing import Any, Optional

class ConfiguracionSistema:
    """Singleton que almacena la configuración global de la aplicación."""
    _instancia: Optional["ConfiguracionSistema"] = None

    def __new__(cls) -> "ConfiguracionSistema":
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._valores = {}
            cls._instancia._inicializado = True
        return cls._instancia

    def set(self, clave: str, valor: Any) -> None:
        self._valores[clave] = valor

    def get(self, clave: str, por_defecto: Any = None) -> Any:
        return self._valores.get(clave, por_defecto)

    def limpiar(self) -> None:
        self._valores.clear()
```

### Archivo: `main.py`
```python
from configuracion.config_sistema import ConfiguracionSistema

def main():
    # Obtención de referencias en distintas partes del programa
    config_a = ConfiguracionSistema()
    config_a.set("api_url", "https://api.empresa.com/v1")
    config_a.set("timeout_segundos", 30)

    config_b = ConfiguracionSistema()

    # Comprobación de identidad
    print(f"¿Misma instancia? {config_a is config_b}")         # True
    print(f"¿Mismo ID de memoria? {id(config_a) == id(config_b)}") # True
    print(f"API URL leída desde config_b: {config_b.get('api_url')}")

if __name__ == "__main__":
    main()
```

---

## Cuidado con `__init__` en Singletons

En Python, cada vez que se llama a `Clase()`, el intérprete ejecuta `__new__` y seguidamente **vuelve a invocar `__init__`**, incluso si `__new__` devolvió una instancia existente.

```python
# ❌ ERROR COMÚN: Reinicializar atributos en cada invocación
def __init__(self):
    self._valores = {}  # ¡Borraría la configuración en cada llamada a ConfiguracionSistema()!

# ✅ SOLUCIÓN: Inicializar en __new__ o controlar con una bandera
def __init__(self):
    if hasattr(self, "_inicializado"):
        return
    self._valores = {}
    self._inicializado = True
```

---

## Reglas para Agentes de IA

1. **Implementar con `__new__`**: No simular singletons mediante variables globales de módulo a menos que se trate de una constante pura.
2. **Controlar la re-inicialización**: Asegure que los atributos del estado interno solo se creen la primera vez.
3. **No abusar**: No convierta entidades de negocio ordinarias en Singletons. El Singleton es una herramienta de infraestructura y configuración.
