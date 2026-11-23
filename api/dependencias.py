# -*- coding: utf-8 -*-
"""Inyección de dependencias de la API.

La ruta de la base SQLite se lee en cada petición desde ``DB_PATH``. Si existe
``DATABASE_URL`` se usa PostgreSQL/Supabase en el esquema ``aqsis``. Así las
pruebas pueden usar una base temporal sin tocar la base de desarrollo, y el
mismo contrato de repositorio sirve para los dos motores.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from persistencia.repositorio import RepositorioMascotas
from persistencia.repositorio_postgres import RepositorioPostgres
from servicios.servicio_catalogo import ServicioCatalogo
from servicios.servicio_mascotas import ServicioMascotas

RAIZ = Path(__file__).resolve().parent.parent
Repositorio = RepositorioMascotas | RepositorioPostgres


def obtener_ruta_db() -> str:
    return os.environ.get("DB_PATH", str(RAIZ / "evidencias" / "api.db"))


def obtener_dsn() -> str | None:
    return os.environ.get("DATABASE_URL") or None


@lru_cache(maxsize=8)
def _repositorio_postgres(dsn: str) -> RepositorioPostgres:
    return RepositorioPostgres(dsn)


def obtener_repositorio(
    ruta_db: str = Depends(obtener_ruta_db),
    dsn: str | None = Depends(obtener_dsn),
) -> Repositorio:
    if dsn:
        return _repositorio_postgres(dsn)
    return RepositorioMascotas(ruta_db)


def obtener_servicio_mascotas(
    repositorio: Repositorio = Depends(obtener_repositorio),
) -> ServicioMascotas:
    return ServicioMascotas(repositorio)


def obtener_servicio_catalogo(
    repositorio: Repositorio = Depends(obtener_repositorio),
) -> ServicioCatalogo:
    return ServicioCatalogo(repositorio)
