# -*- coding: utf-8 -*-
"""Fixtures compartidas de las pruebas de la semana 14."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA = RAIZ / "persistencia" / "schema.sql"
SEED = RAIZ / "persistencia" / "seed.sql"


def crear_base(ruta: Path) -> None:
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(SCHEMA.read_text(encoding="utf-8"))
        conexion.executescript(SEED.read_text(encoding="utf-8"))
        conexion.commit()


@pytest.fixture()
def ruta_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base limpia y aislada por prueba."""
    ruta = tmp_path / "prueba.db"
    crear_base(ruta)
    monkeypatch.setenv("DB_PATH", str(ruta))
    return ruta


@pytest.fixture()
def cliente(ruta_db: Path):
    with TestClient(app) as cliente_http:
        yield cliente_http


def datos_mascota(**cambios) -> dict:
    """Cuerpo válido para POST /mascotas (refugio verificado 1)."""
    datos = {
        "refugio_id": 1,
        "nombre": "Nala",
        "raza": "Mestiza",
        "especie": "perro",
        "edad_meses": 24,
        "tamano": "mediano",
        "nivel_energia": "media",
        "experiencia_requerida": "basica",
        "apta_con_menores": True,
        "apta_con_mascotas": True,
        "historial_salud": "Vacunas al día",
        "historial_comportamiento": "Sociable",
        "fecha_publicacion": "2026-10-10",
        "fotografias": ["nala_01.jpg", "nala_02.jpg"],
    }
    datos.update(cambios)
    return datos


def contar(ruta_db: Path, tabla: str) -> int:
    with sqlite3.connect(ruta_db) as conexion:
        return int(conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])
