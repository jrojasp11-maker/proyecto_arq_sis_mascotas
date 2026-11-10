# -*- coding: utf-8 -*-
"""Inyección de dependencias de la API.

La ruta de la base se lee en cada petición desde ``DB_PATH``. Así las pruebas
pueden usar una base temporal sin tocar la base de desarrollo.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends

from persistencia.repositorio import RepositorioMascotas
from servicios.servicio_catalogo import ServicioCatalogo
from servicios.servicio_mascotas import ServicioMascotas

RAIZ = Path(__file__).resolve().parent.parent


def obtener_ruta_db() -> str:
    return os.environ.get("DB_PATH", str(RAIZ / "evidencias" / "api.db"))


def obtener_repositorio(
    ruta_db: str = Depends(obtener_ruta_db),
) -> RepositorioMascotas:
    return RepositorioMascotas(ruta_db)


def obtener_servicio_mascotas(
    repositorio: RepositorioMascotas = Depends(obtener_repositorio),
) -> ServicioMascotas:
    return ServicioMascotas(repositorio)


def obtener_servicio_catalogo(
    repositorio: RepositorioMascotas = Depends(obtener_repositorio),
) -> ServicioCatalogo:
    return ServicioCatalogo(repositorio)
