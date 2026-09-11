"""Capa de infraestructura: adaptadores concretos de persistencia (PyMongo, Paso 5).

El dominio y los servicios de aplicación nunca importan nada de aquí
directamente (Dependency Inversion): dependen de las interfaces abstractas
de `app/usuarios/repositorio.py` y `app/requerimientos/repositorio.py`. Es
`app/deps.py` quien conecta ambos mundos.
"""
