# -*- coding: utf-8 -*-
"""Fixtures compartidas de las pruebas de las semanas 14 y 15."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app

RAIZ = Path(__file__).resolve().parent.parent
SCHEMA = RAIZ / "persistencia" / "schema.sql"
SEED = RAIZ / "persistencia" / "seed.sql"
CLAVE_DEMO = "Aqsis2026!"
SECRETO_PRUEBAS = "aqsis-secreto-de-pruebas-largo-2026-corte-vertical"


def crear_base(ruta: Path) -> None:
    with sqlite3.connect(ruta) as conexion:
        conexion.executescript(SCHEMA.read_text(encoding="utf-8"))
        conexion.executescript(SEED.read_text(encoding="utf-8"))
        conexion.commit()


def token_de(cliente: TestClient, usuario: str) -> str:
    respuesta = cliente.post(
        "/api/v1/auth/token",
        json={"usuario": usuario, "contrasena": CLAVE_DEMO},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


@pytest.fixture()
def ruta_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Base SQLite limpia y aislada por prueba; ignora DATABASE_URL del entorno."""
    ruta = tmp_path / "prueba.db"
    crear_base(ruta)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AUTH_JWT_SECRET", SECRETO_PRUEBAS)
    monkeypatch.setenv("DB_PATH", str(ruta))
    return ruta


@pytest.fixture()
def cliente_sin_token(ruta_db: Path):
    """Cliente sin cabecera Authorization para probar el rechazo 401."""
    with TestClient(app) as cliente_http:
        yield cliente_http


@pytest.fixture()
def cliente(ruta_db: Path):
    """Cliente autenticado como refugio (propietario del refugio 1)."""
    with TestClient(app) as cliente_http:
        cliente_http.headers.update(
            {"Authorization": f"Bearer {token_de(cliente_http, 'refugio')}"}
        )
        yield cliente_http


@pytest.fixture()
def cliente_adoptante(ruta_db: Path):
    with TestClient(app) as cliente_http:
        cliente_http.headers.update(
            {"Authorization": f"Bearer {token_de(cliente_http, 'adoptante')}"}
        )
        yield cliente_http


@pytest.fixture()
def cliente_admin(ruta_db: Path):
    with TestClient(app) as cliente_http:
        cliente_http.headers.update(
            {"Authorization": f"Bearer {token_de(cliente_http, 'admin')}"}
        )
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
