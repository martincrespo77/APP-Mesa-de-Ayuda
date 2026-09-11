# 08. Patrón de Comportamiento: Observer

El patrón **Observer** establece una relación de dependencia uno a muchos (*1:N*) entre objetos, de modo que cuando el objeto principal (**Sujeto** u **Observable**) cambia su estado, todos sus dependientes (**Observadores**) son notificados de manera automática y desacoplada.

---

## Estructura Modular

```
notificaciones/
├── __init__.py
├── observador.py         # Interfaz abstracta Observador
├── sujeto.py             # Clase Sujeto (Observable)
├── observador_logger.py  # Observador concreto: Logger
└── observador_email.py   # Observador concreto: Alerta por Email
```

---

## Código de Implementación

### Archivo: `notificaciones/observador.py`
```python
from abc import ABC, abstractmethod
from typing import Any

class Observador(ABC):
    """Interfaz que deben implementar todos los suscriptores."""
    @abstractmethod
    def actualizar(self, evento: str, datos: Any) -> None:
        pass
```

### Archivo: `notificaciones/sujeto.py`
```python
from typing import List, Any
from .observador import Observador

class Sujeto:
    """Clase base para objetos observables que gestionan suscriptores."""
    def __init__(self):
        self._observadores: List[Observador] = []
        self._estado: Any = None

    def agregar_observador(self, observador: Observador) -> None:
        if observador not in self._observadores:
            self._observadores.append(observador)

    def remover_observador(self, observador: Observador) -> None:
        if observador in self._observadores:
            self._observadores.remove(observador)

    def notificar(self, evento: str, datos: Any) -> None:
        for obs in self._observadores:
            obs.actualizar(evento, datos)

    def cambiar_estado(self, nuevo_estado: Any, evento: str = "CAMBIO_ESTADO") -> None:
        self._estado = nuevo_estado
        self.notificar(evento, nuevo_estado)
```

### Archivo: `notificaciones/observador_logger.py`
```python
from typing import Any
from .observador import Observador

class ObservadorLogger(Observador):
    def __init__(self, prefijo: str = "AUDITORIA"):
        self.prefijo = prefijo

    def actualizar(self, evento: str, datos: Any) -> None:
        print(f"[{self.prefijo}] Evento detectado: '{evento}' con datos: {datos}")
```

### Archivo: `notificaciones/observador_email.py`
```python
from typing import Any
from .observador import Observador

class ObservadorEmail(Observador):
    def __init__(self, destinatario: str):
        self.destinatario = destinatario

    def actualizar(self, evento: str, datos: Any) -> None:
        if "CRITICO" in evento.upper():
            print(f"📧 Enviando correo de urgencia a {self.destinatario}: {datos}")
```

### Archivo: `main.py`
```python
from notificaciones.sujeto import Sujeto
from notificaciones.observador_logger import ObservadorLogger
from notificaciones.observador_email import ObservadorEmail

def main():
    monitor = Sujeto()
    logger = ObservadorLogger("SISTEMA_METRICAS")
    alerta_email = ObservadorEmail("ops@empresa.com")

    monitor.agregar_observador(logger)
    monitor.agregar_observador(alerta_email)

    # Evento ordinario
    monitor.cambiar_estado({"cpu": 45, "ram": 55}, evento="METRICAS_NORMAL")

    # Evento crítico: Notifica al logger y además dispara el email
    monitor.cambiar_estado({"cpu": 98, "ram": 92}, evento="ALERTA_CRITICO")

if __name__ == "__main__":
    main()
```

---

## Ventajas del Patrón

1. **Bajo Acoplamiento**: El Sujeto no necesita saber qué hacen los observadores (si guardan en disco, mandan un mensaje de WhatsApp o envían un mail). Solo conoce el contrato `actualizar()`.
2. **Principio Abierto/Cerrado (OCP)**: Se pueden añadir observadores nuevos sin tocar una sola línea de la clase Sujeto.
3. **Suscripción Dinámica**: Se pueden registrar y remover observadores en tiempo de ejecución.

---

## Directivas para Agentes de IA

- **No acoplar el sujeto a canales específicos**: Jamás importe `EmailService` dentro de `Sujeto` o de una entidad de negocio. Use la abstracción `Observador`.
- **Manejar listas limpias**: Compruebe que no se duplique un observador en `agregar_observador` y gestione remociones seguras.
