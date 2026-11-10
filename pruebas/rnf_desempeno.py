# -*- coding: utf-8 -*-
"""Verificación acotada del RNF-05 (eficiencia de desempeño / tiempo).

Escenario:
  - 1.000 fichas disponibles en un entorno local documentado.
  - 20 consultas consecutivas al catálogo por HTTP real.
  - Umbral: cada consulta debe responder en <= 1.000 ms.

No sustituye la prueba de concurrencia de la semana 3; mide el comportamiento
temporal secuencial sobre la API.

Uso:
    python -m pruebas.rnf_desempeno
"""

from __future__ import annotations

import datetime as dt
import math
import sqlite3
import statistics
import sys
import time
from contextlib import closing
from pathlib import Path

import fastapi
import httpx
import uvicorn

from pruebas.servidor import servidor_api

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"
SCHEMA = RAIZ / "persistencia" / "schema.sql"
SEED = RAIZ / "persistencia" / "seed.sql"
RUTA_DB = EVIDENCIAS / "rnf_desempeno.db"
SALIDA = EVIDENCIAS / "rnf_desempeno.txt"

FICHAS = 1000
CONSULTAS = 20
UMBRAL_MS = 1000.0


def recrear_base() -> int:
    """Recrea la base y deja exactamente ``FICHAS`` fichas publicadas."""
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    if RUTA_DB.exists():
        RUTA_DB.unlink()

    base = dt.date(2026, 1, 1)
    fichas = []
    for indice in range(1, FICHAS + 1):
        fichas.append(
            (
                1,
                f"Mascota {indice:04d}",
                "perro" if indice % 2 else "gato",
                12 + (indice % 120),
                "pequeno" if indice % 3 == 0 else "mediano",
                "media",
                "basica",
                1,
                1,
                "disponible",
                (base + dt.timedelta(days=indice % 365)).isoformat(),
            )
        )

    with closing(sqlite3.connect(RUTA_DB)) as conexion:
        conexion.executescript(SCHEMA.read_text(encoding="utf-8"))
        conexion.executescript(SEED.read_text(encoding="utf-8"))
        conexion.execute("DELETE FROM fotografia")
        conexion.execute("DELETE FROM mascota")
        conexion.executemany(
            """
            INSERT INTO mascota (
                refugio_id, nombre, especie, edad_meses, tamano,
                nivel_energia, experiencia_requerida, apta_con_menores,
                apta_con_mascotas, estado, fecha_publicacion
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fichas,
        )
        identificadores = [
            fila[0] for fila in conexion.execute("SELECT id FROM mascota")
        ]
        conexion.executemany(
            "INSERT INTO fotografia (mascota_id, archivo, orden) VALUES (?, ?, 1)",
            [(mascota_id, f"mascota_{mascota_id:04d}.jpg") for mascota_id in identificadores],
        )
        conexion.commit()
        return int(conexion.execute("SELECT COUNT(*) FROM mascota").fetchone()[0])


def main() -> int:
    total_fichas = recrear_base()
    registros: list[tuple[int, int, float, int]] = []

    with servidor_api(RUTA_DB) as url_base:
        with httpx.Client(base_url=url_base, timeout=10) as cliente:
            cliente.get("/api/v1/mascotas", params={"pagina": 1, "por_pagina": 20})

            for numero in range(1, CONSULTAS + 1):
                inicio = time.perf_counter()
                respuesta = cliente.get(
                    "/api/v1/mascotas",
                    params={"pagina": 1, "por_pagina": 20},
                )
                milisegundos = (time.perf_counter() - inicio) * 1000
                registros.append(
                    (
                        numero,
                        respuesta.status_code,
                        milisegundos,
                        int(respuesta.json().get("total", -1)),
                    )
                )

    tiempos = [registro[2] for registro in registros]
    cumplen = sum(
        1
        for _, estado, milisegundos, total in registros
        if estado == 200 and total == total_fichas and milisegundos <= UMBRAL_MS
    )
    correctos = sum(
        1
        for _, estado, _, total in registros
        if estado == 200 and total == total_fichas
    )
    p95 = sorted(tiempos)[max(0, math.ceil(0.95 * len(tiempos)) - 1)]

    lineas = [
        "RNF-05 - EFICIENCIA DE DESEMPEÑO / COMPORTAMIENTO TEMPORAL",
        "=" * 78,
        f"Fecha de ejecución: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Python: {sys.version.split()[0]} | SQLite: {sqlite3.sqlite_version}",
        f"FastAPI: {fastapi.__version__} | Uvicorn: {uvicorn.__version__}",
        f"Base de datos: {RUTA_DB}",
        f"Fichas publicadas: {total_fichas}",
        f"Consultas consecutivas: {CONSULTAS}",
        f"Umbral por consulta: <= {UMBRAL_MS:.0f} ms",
        "Métrica: tiempo completo de la respuesta HTTP medida por el cliente.",
        "Alcance: verificación secuencial; la concurrencia de 50 usuarios queda para la semana 3.",
        "-" * 78,
        f"{'#':>3}  {'HTTP':>4}  {'ms':>9}  {'total':>6}",
        "-" * 78,
    ]
    for numero, estado, milisegundos, total in registros:
        lineas.append(
            f"{numero:>3}  {estado:>4}  {milisegundos:>9.2f}  {total:>6}"
        )
    lineas.extend(
        [
            "-" * 78,
            f"Respuestas correctas (200 y total={total_fichas}): {correctos}/{CONSULTAS}",
            f"Consultas dentro del umbral: {cumplen}/{CONSULTAS}",
            f"Mínimo: {min(tiempos):.2f} ms",
            f"Promedio: {statistics.mean(tiempos):.2f} ms",
            f"p95: {p95:.2f} ms",
            f"Máximo: {max(tiempos):.2f} ms",
            "-" * 78,
        ]
    )

    if correctos == CONSULTAS and cumplen == CONSULTAS:
        lineas.append("RESULTADO: CUMPLE (verificación secuencial).")
        codigo = 0
    else:
        lineas.append("RESULTADO: NO CUMPLE. Revise los registros anteriores.")
        codigo = 1

    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    print(f"\nEvidencia escrita en: {SALIDA}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
