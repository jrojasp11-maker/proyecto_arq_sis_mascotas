# -*- coding: utf-8 -*-
"""Servidor Uvicorn temporal para las verificaciones por HTTP real."""

from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
from collections.abc import Iterator

import uvicorn


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_temporal:
        socket_temporal.bind(("127.0.0.1", 0))
        return int(socket_temporal.getsockname()[1])


@contextlib.contextmanager
def servidor_api(ruta_db: str, puerto: int | None = None) -> Iterator[str]:
    """Levanta la API en un hilo y entrega la URL base; la apaga al salir."""
    from api.main import app

    os.environ["DB_PATH"] = str(ruta_db)
    puerto = puerto or _puerto_libre()

    configuracion = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=puerto,
        log_level="warning",
        access_log=False,
    )
    servidor = uvicorn.Server(configuracion)
    hilo = threading.Thread(
        target=servidor.run, name="uvicorn-temporal", daemon=True
    )
    hilo.start()

    limite = time.time() + 15
    while not servidor.started:
        if time.time() > limite:
            raise RuntimeError("El servidor de prueba no inició a tiempo")
        time.sleep(0.05)

    try:
        yield f"http://127.0.0.1:{puerto}"
    finally:
        servidor.should_exit = True
        hilo.join(timeout=10)
