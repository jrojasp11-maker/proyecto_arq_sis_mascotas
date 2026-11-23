# -*- coding: utf-8 -*-
"""Punto de entrada para Vercel del corte vertical (RF-05 y RF-34).

Vercel detecta automaticamente una instancia ``app`` de FastAPI en ``main.py``.
Este modulo solo prepara la base de datos y reexporta la aplicacion real de
``api/main.py``: no cambia contratos ni reglas de negocio.

Con ``DATABASE_URL`` se usa PostgreSQL/Supabase de forma persistente. Si no hay
base externa y el codigo corre en Vercel, se usa una base efimera en ``/tmp``
solo para probar el recorrido; en local se respeta ``DB_PATH``.
"""

from __future__ import annotations

import os
from pathlib import Path

if os.environ.get("VERCEL") and not os.environ.get("DATABASE_URL"):
    os.environ.setdefault("DB_PATH", "/tmp/aqsis_api.db")
    from persistencia.inicializar_db import inicializar

    ruta_db = Path(os.environ["DB_PATH"])
    if not ruta_db.exists():
        inicializar(ruta_db)

from api.main import app  # noqa: E402

__all__ = ["app"]
