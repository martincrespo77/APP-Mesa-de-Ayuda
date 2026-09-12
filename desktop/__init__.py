"""Frontend de escritorio (PyQt6), completamente independiente de `app/`.

No importa clases ni modelos del backend (doc05): toda la comunicación
ocurre vía HTTP (`api_client.py`), y los tipos propios de esta capa viven
en `models.py` — coinciden por contrato con los schemas de la API, pero
no comparten código con ellos.
"""
