# -*- coding: utf-8 -*-
"""Servidor Uvicorn temporal para las verificaciones por HTTP real."""

from __future__ import annotations

import contextlib
import os
import socket
import threading
import time
from collections.abc import Iterator

import httpx
import uvicorn

CLAVE_DEMO = "Aqsis2026!"


def token_de_cliente(cliente: httpx.Client, usuario: str = "adoptante") -> str:
    """Obtiene un JWT de prueba para las verificaciones por HTTP real."""
    respuesta = cliente.post(
        "/api/v1/auth/token",
        json={"usuario": usuario, "contrasena": CLAVE_DEMO},
    )
    respuesta.raise_for_status()
    return respuesta.json()["access_token"]


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_temporal:
        socket_temporal.bind(("127.0.0.1", 0))
        return int(socket_temporal.getsockname()[1])


@contextlib.contextmanager
def servidor_api(
    ruta_db: str | None = None,
    puerto: int | None = None,
    workers: int = 1,
    usar_postgres: bool = False,
) -> Iterator[str]:
    """Levanta la API y entrega la URL base; la apaga al salir.

    ``workers`` permite reproducir una instalación con varios procesos, como
    ocurre en un despliegue real. Con un solo proceso se usa el objeto ``app``
    directamente para no depender del importador de Uvicorn. Con
    ``usar_postgres=True`` se conserva ``DATABASE_URL`` para apuntar a Supabase.
    """
    from api.main import app

    if usar_postgres:
        os.environ.pop("DB_PATH", None)
    else:
        if ruta_db is None:
            raise ValueError("ruta_db es obligatoria cuando no se usa PostgreSQL")
        os.environ["DB_PATH"] = str(ruta_db)
        os.environ.pop("DATABASE_URL", None)
    os.environ.setdefault(
        "AUTH_JWT_SECRET", "aqsis-secreto-local-pruebas-largo-2026-corte-vertical"
    )
    puerto = puerto or _puerto_libre()
    objetivo = "api.main:app" if workers > 1 else app

    configuracion = uvicorn.Config(
        objetivo,
        host="127.0.0.1",
        port=puerto,
        log_level="warning",
        access_log=False,
        workers=workers,
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
