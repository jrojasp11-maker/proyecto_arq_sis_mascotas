# -*- coding: utf-8 -*-
"""Crea o reinicia la base de datos local de la API.

Uso:
    python -m persistencia.inicializar_db

La ruta se toma de la variable ``DB_PATH``. Si no existe, se usa
``evidencias/api.db``. El comando borra la base anterior y la recrea con
``schema.sql`` + ``seed.sql`` para dejar un estado conocido.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import closing
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = Path(__file__).resolve().parent
SCHEMA = CARPETA / "schema.sql"
SEED = CARPETA / "seed.sql"


def ruta_por_defecto() -> Path:
    return Path(os.environ.get("DB_PATH", RAIZ / "evidencias" / "api.db"))


def inicializar(ruta: str | Path | None = None) -> Path:
    """Recrea la base en ``ruta`` y devuelve la ruta final."""
    destino = Path(ruta) if ruta is not None else ruta_por_defecto()
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        destino.unlink()

    with closing(sqlite3.connect(destino)) as conexion:
        conexion.executescript(SCHEMA.read_text(encoding="utf-8"))
        conexion.executescript(SEED.read_text(encoding="utf-8"))
        conexion.commit()

    return destino


def main() -> None:
    destino = inicializar()
    print(f"Base de datos creada: {destino}")
    print("Inicie la API con: uvicorn api.main:app --reload --port 8000")


if __name__ == "__main__":
    main()
