# -*- coding: utf-8 -*-
"""RNF-05 y RNF-07 medidos por HTTP real contra PostgreSQL/Supabase.

Carga 1.000 y 2.000 fichas en el esquema aqsis, ejecuta las mismas consultas
del catálogo que la interfaz y al final restaura la carga inicial con
``persistencia.migrar_supabase``. No imprime credenciales.

Uso:
    python -m pruebas.rnf_supabase
"""

from __future__ import annotations

import datetime as dt
import os
import statistics
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from persistencia.migrar_supabase import cargar_env_local
from pruebas.rnf_escalabilidad import medir, percentil95, resumen
from pruebas.servidor import servidor_api

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "evidencias" / "rnf_supabase.txt"
FICHAS_05 = 1000
FICHAS_07 = 2000
USUARIOS = 50
CONSULTAS_POR_USUARIO = 20
ADOPTANTES = 5000
HILOS = 50
CONSULTAS_SECUENCIALES = 20
UMBRAL_MS = 1000.0


def cargar_fichas(motor, cantidad: int) -> int:
    """Deja exactamente ``cantidad`` fichas disponibles con una foto cada una.

    La carga se hace con una sola sentencia SQL por tabla: evita el modo
    pipelining de psycopg con el pooler y es reproducible.
    """
    with motor.begin() as conexion:
        conexion.execute(text("DELETE FROM aqsis.fotografia"))
        conexion.execute(text("DELETE FROM aqsis.mascota"))
        conexion.execute(
            text(
                """
                INSERT INTO aqsis.mascota (
                    refugio_id, nombre, especie, edad_meses, tamano,
                    nivel_energia, experiencia_requerida, apta_con_menores,
                    apta_con_mascotas, estado, fecha_publicacion
                )
                SELECT 1,
                       'Mascota ' || lpad(i::text, 4, '0'),
                       CASE WHEN i % 2 = 1 THEN 'perro' ELSE 'gato' END,
                       12 + (i % 120),
                       CASE WHEN i % 3 = 0 THEN 'pequeno' ELSE 'mediano' END,
                       'media', 'basica', 1, 1, 'disponible',
                       (DATE '2026-01-01' + ((i % 365) || ' days')::interval)::date
                FROM generate_series(1, :cantidad) AS i
                """
            ),
            {"cantidad": cantidad},
        )
        conexion.execute(
            text(
                """
                INSERT INTO aqsis.fotografia (mascota_id, archivo, orden)
                SELECT id, 'mascota_' || lpad(id::text, 4, '0') || '.jpg', 1
                FROM aqsis.mascota
                """
            )
        )
        identificadores = conexion.execute(
            text("SELECT id FROM aqsis.mascota ORDER BY id")
        ).scalars().all()
        conexion.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('aqsis.mascota', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM aqsis.mascota), true)"
            )
        )
        conexion.execute(
            text(
                "SELECT setval(pg_get_serial_sequence('aqsis.fotografia', 'id'), "
                "(SELECT COALESCE(MAX(id), 1) FROM aqsis.fotografia), true)"
            )
        )
    return len(identificadores)


def main() -> int:
    cargar_env_local()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Falta DATABASE_URL en .env.local")
    motor = create_engine(dsn, pool_pre_ping=True)

    lineas: list[str] = [
        "RNF-05 Y RNF-07 CON POSTGRESQL/SUPABASE - VERIFICACION HTTP REAL",
        "=" * 78,
        f"Fecha de ejecucion: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Python: {sys.version.split()[0]}",
        "Base: PostgreSQL/Supabase | Esquema: aqsis",
        "Servidor: Uvicorn temporal con 4 procesos | Cliente: httpx",
        "Las respuestas vienen de la API real; no se simulan tiempos ni datos.",
        "=" * 78,
        "",
    ]

    try:
        total_05 = cargar_fichas(motor, FICHAS_05)
        with servidor_api(usar_postgres=True, workers=4) as url_base:
            with httpx.Client(
                base_url=url_base,
                timeout=30,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            ) as cliente:
                respuesta_token = cliente.post(
                    "/api/v1/auth/token",
                    json={"usuario": "adoptante", "contrasena": "Aqsis2026!"},
                )
                respuesta_token.raise_for_status()
                cliente.headers.update(
                    {"Authorization": f"Bearer {respuesta_token.json()['access_token']}"}
                )

                secuenciales: list[float] = []
                for _ in range(CONSULTAS_SECUENCIALES):
                    inicio = time.perf_counter()
                    respuesta = cliente.get(
                        "/api/v1/mascotas", params={"pagina": 1, "por_pagina": 20}
                    )
                    secuenciales.append((time.perf_counter() - inicio) * 1000)
                    if respuesta.status_code != 200:
                        raise RuntimeError(f"consulta secuencial HTTP {respuesta.status_code}")

                registros_05, reintentos_05 = medir(
                    cliente,
                    total_05,
                    USUARIOS * CONSULTAS_POR_USUARIO,
                    USUARIOS,
                )

            lineas.extend(
                [
                    f"RNF-05 secuencial | {FICHAS_05} fichas | {CONSULTAS_SECUENCIALES} consultas",
                    "-" * 78,
                    f"Respuestas correctas: {CONSULTAS_SECUENCIALES}/{CONSULTAS_SECUENCIALES}",
                    f"Minimo: {min(secuenciales):.2f} ms",
                    f"Promedio: {statistics.mean(secuenciales):.2f} ms",
                    f"p95: {percentil95(secuenciales):.2f} ms",
                    f"Maximo: {max(secuenciales):.2f} ms",
                    f"Criterio: cada consulta <= {UMBRAL_MS:.0f} ms",
                    "RESULTADO: "
                    + ("CUMPLE" if max(secuenciales) <= UMBRAL_MS else "NO CUMPLE"),
                    "",
                ]
            )
            resumen_05, cumple_05 = resumen(
                "RNF-05 concurrente - 50 usuarios sobre PostgreSQL",
                registros_05,
                total_05,
                UMBRAL_MS,
                criterio="p95",
                reintentos=reintentos_05,
            )
            lineas.extend(resumen_05)
            lineas.append("")

            total_07 = cargar_fichas(motor, FICHAS_07)
            with httpx.Client(
                base_url=url_base,
                timeout=30,
                limits=httpx.Limits(max_connections=HILOS, max_keepalive_connections=HILOS),
            ) as cliente:
                respuesta_token = cliente.post(
                    "/api/v1/auth/token",
                    json={"usuario": "adoptante", "contrasena": "Aqsis2026!"},
                )
                respuesta_token.raise_for_status()
                cliente.headers.update(
                    {"Authorization": f"Bearer {respuesta_token.json()['access_token']}"}
                )
                registros_07, reintentos_07 = medir(
                    cliente, total_07, ADOPTANTES, HILOS
                )

            lineas.extend(
                [
                    f"RNF-07 | {FICHAS_07} fichas | {ADOPTANTES} adoptantes "
                    f"(consultas con rol adoptante) | {HILOS} hilos",
                    "Cada adoptante se modela como una consulta al catalogo con JWT.",
                    "-" * 78,
                ]
            )
            resumen_07, cumple_07 = resumen(
                "RNF-07 escalabilidad sobre PostgreSQL",
                registros_07,
                total_07,
                UMBRAL_MS,
                criterio="p95",
                reintentos=reintentos_07,
            )
            lineas.extend(resumen_07)

        cumple_secuencial = max(secuenciales) <= UMBRAL_MS
        lineas.extend(
            [
                "",
                "=" * 78,
                "RESULTADO FINAL: "
                + (
                    "CUMPLE. RNF-05 y RNF-07 verificados contra Supabase."
                    if cumple_05 and cumple_07 and cumple_secuencial
                    else "NO CUMPLE. Revise los resultados anteriores."
                ),
                "=" * 78,
            ]
        )
        codigo = 0 if cumple_05 and cumple_07 and cumple_secuencial else 1
    finally:
        # Restaura el estado inicial del corte para que la demo quede limpia.
        from persistencia.migrar_supabase import main as restaurar

        restaurar()

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[-22:]))
    print(f"\nEvidencia escrita en: {SALIDA}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
