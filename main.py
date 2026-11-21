# -*- coding: utf-8 -*-
"""Punto de entrada para Vercel del corte vertical (RF-05 y RF-34).

Vercel detecta automaticamente una instancia ``app`` de FastAPI en ``main.py``.
Este modulo solo prepara la base de datos y reexporta la aplicacion real de
``api/main.py``: no cambia contratos ni reglas de negocio.

En Vercel el sistema de archivos es de solo lectura salvo ``/tmp``. Por eso se
usa una base efimera: sirve para probar el recorrido completo, pero no conserva
datos entre instancias ni despliegues. En local se respeta ``DB_PATH``.
"""

from __future__ import annotations

import os
from pathlib import Path

if os.environ.get("VERCEL"):
    os.environ.setdefault("DB_PATH", "/tmp/aqsis_api.db")
    from persistencia.inicializar_db import inicializar

    ruta_db = Path(os.environ["DB_PATH"])
    if not ruta_db.exists():
        inicializar(ruta_db)

from api.main import app  # noqa: E402

__all__ = ["app"]
