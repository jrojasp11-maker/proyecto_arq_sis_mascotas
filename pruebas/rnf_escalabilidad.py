# -*- coding: utf-8 -*-
"""Cierre de RNF-05 (concurrencia) y RNF-07 (escalabilidad) por HTTP real.

Escenarios:
  A) RNF-05: 1.000 fichas, 50 usuarios concurrentes, 20 consultas por usuario.
     Umbral: p95 de la respuesta HTTP <= 1.000 ms (en secuencial se conserva
     el criterio mas estricto: cada consulta <= 1.000 ms).
  B) RNF-07: 2.000 fichas, 5.000 adoptantes simulados como consultas al
     catálogo, 50 usuarios concurrentes. Umbral: p95 <= 1.000 ms.

El rol ``adoptante`` forma parte de la autenticación desde la semana 15: cada
adoptante se modela como una petición HTTP autenticada al catálogo (RF-34), que
es la operación que el RNF evalúa. No se simulan respuestas: todas vienen de la
API real.

Uso:
    python -m pruebas.rnf_escalabilidad
"""

from __future__ import annotations

import datetime as dt
import math
import platform
import sqlite3
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import fastapi
import httpx
import uvicorn

from pruebas.rnf_desempeno import recrear_base
from pruebas.servidor import servidor_api, token_de_cliente

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"
SALIDA = EVIDENCIAS / "rnf_escalabilidad.txt"

FICHAS_RNF05 = 1000
USUARIOS_RNF05 = 50
CONSULTAS_POR_USUARIO = 20
FICHAS_RNF07 = 2000
ADOPTANTES_RNF07 = 5000
HILOS = 50
UMBRAL_MS = 1000.0


def percentil95(valores: list[float]) -> float:
    """Percentil 95 por rango más cercano (nearest-rank)."""
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(0.95 * len(ordenados)) - 1)]


def medir(
    cliente: httpx.Client,
    total_esperado: int,
    cantidad: int,
    hilos: int,
) -> tuple[list[tuple[int, float, int, int]], int]:
    """Ejecuta consultas concurrentes; devuelve registros y reintentos por corte HTTP."""
    reintentos: list[int] = []

    def consulta(indice: int) -> tuple[int, float, int, int]:
        inicio = time.perf_counter()
        estado = 0
        total = -1
        for intento in range(3):
            try:
                respuesta = cliente.get(
                    "/api/v1/mascotas",
                    params={"pagina": 1, "por_pagina": 20},
                )
                estado = respuesta.status_code
                total = int(respuesta.json().get("total", -1)) if estado == 200 else -1
                break
            except httpx.HTTPError:
                if intento < 2:
                    reintentos.append(1)
        milisegundos = (time.perf_counter() - inicio) * 1000
        return indice, milisegundos, estado, total

    with ThreadPoolExecutor(max_workers=hilos) as ejecutor:
        registros = list(ejecutor.map(consulta, range(1, cantidad + 1)))
    return registros, len(reintentos)


def resumen(
    nombre: str,
    registros: list[tuple[int, float, int, int]],
    total_esperado: int,
    umbral: float,
    criterio: str = "cada",
    reintentos: int = 0,
) -> tuple[list[str], bool]:
    """Resume una medición; ``criterio`` es ``cada`` petición o ``p95``."""
    tiempos = [registro[1] for registro in registros]
    correctos = sum(
        1 for _, _, estado, total in registros
        if estado == 200 and total == total_esperado
    )
    dentro = sum(1 for tiempo in tiempos if tiempo <= umbral)
    p95 = percentil95(tiempos)
    cumple = correctos == len(registros) and (
        p95 <= umbral if criterio == "p95" else dentro == len(registros)
    )
    lentos = sorted(registros, key=lambda registro: registro[1], reverse=True)[:5]

    lineas = [
        nombre,
        "-" * 78,
        f"Peticiones ejecutadas: {len(registros)}",
        f"Reintentos por corte de conexion: {reintentos}",
        f"Respuestas correctas (HTTP 200 y total={total_esperado}): {correctos}/{len(registros)}",
        f"Respuestas dentro del umbral (<= {umbral:.0f} ms): {dentro}/{len(registros)}",
        f"Criterio aplicado: {'p95 <= ' + format(umbral, '.0f') + ' ms' if criterio == 'p95' else 'cada consulta <= ' + format(umbral, '.0f') + ' ms'}",
        f"Minimo: {min(tiempos):.2f} ms",
        f"Promedio: {statistics.mean(tiempos):.2f} ms",
        f"p95: {p95:.2f} ms",
        f"Maximo: {max(tiempos):.2f} ms",
        "Cinco respuestas mas lentas (peticion, ms, HTTP, total):",
    ]
    for indice, milisegundos, estado, total in lentos:
        lineas.append(f"  #{indice:>4}  {milisegundos:>9.2f} ms  {estado}  {total}")
    lineas.append(f"RESULTADO: {'CUMPLE' if cumple else 'NO CUMPLE'}")
    return lineas, cumple


def main() -> int:
    rnf05_db = EVIDENCIAS / "rnf_concurrencia.db"
    rnf07_db = EVIDENCIAS / "rnf_escalabilidad.db"
    total_05 = recrear_base(FICHAS_RNF05, rnf05_db)
    total_07 = recrear_base(FICHAS_RNF07, rnf07_db)

    lineas = [
        "RNF-05 CONCURRENCIA Y RNF-07 ESCALABILIDAD - VERIFICACION HTTP REAL",
        "=" * 78,
        f"Fecha de ejecucion: {dt.datetime.now().isoformat(timespec='seconds')}",
        f"Python: {sys.version.split()[0]} | SQLite: {sqlite3.sqlite_version}",
        f"FastAPI: {fastapi.__version__} | Uvicorn: {uvicorn.__version__}",
        f"Sistema: {platform.system()} {platform.release()} ({platform.processor() or 'CPU'})",
        "Servidor: Uvicorn temporal con 4 procesos, cliente httpx con grupo de hilos.",
        "Metricas: tiempo completo de la respuesta HTTP medido por el cliente.",
        "=" * 78,
        "",
        f"RNF-05 | {FICHAS_RNF05} fichas | {USUARIOS_RNF05} usuarios concurrentes"
        f" | {CONSULTAS_POR_USUARIO} consultas por usuario"
        f" | {USUARIOS_RNF05 * CONSULTAS_POR_USUARIO} peticiones"
        f" | umbral p95 <= {UMBRAL_MS:.0f} ms",
        "-" * 78,
    ]

    with servidor_api(rnf05_db, workers=4) as url_base:
        with httpx.Client(
            base_url=url_base,
            timeout=10,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
        ) as cliente:
            cliente.headers.update(
                {"Authorization": f"Bearer {token_de_cliente(cliente)}"}
            )
            cliente.get("/api/v1/mascotas", params={"pagina": 1, "por_pagina": 20})
            registros_05, reintentos_05 = medir(
                cliente,
                total_05,
                USUARIOS_RNF05 * CONSULTAS_POR_USUARIO,
                USUARIOS_RNF05,
            )

    resumen_05, cumple_05 = resumen(
        "RNF-05 - concurrencia de 50 usuarios",
        registros_05,
        total_05,
        UMBRAL_MS,
        criterio="p95",
        reintentos=reintentos_05,
    )
    lineas.extend(resumen_05)
    lineas.append("")

    lineas.extend(
        [
            f"RNF-07 | {FICHAS_RNF07} fichas | {ADOPTANTES_RNF07} adoptantes simulados"
            f" | {HILOS} usuarios concurrentes | umbral p95 <= {UMBRAL_MS:.0f} ms",
            "-" * 78,
            "Nota de alcance: el corte no modela la entidad adoptante. Cada adoptante",
            "se representa con una consulta al catalogo (RF-34) contra la API real.",
            "-" * 78,
        ]
    )

    with servidor_api(rnf07_db, workers=4) as url_base:
        with httpx.Client(
            base_url=url_base,
            timeout=10,
            limits=httpx.Limits(max_connections=HILOS, max_keepalive_connections=HILOS),
        ) as cliente:
            cliente.headers.update(
                {"Authorization": f"Bearer {token_de_cliente(cliente)}"}
            )
            cliente.get("/api/v1/mascotas", params={"pagina": 1, "por_pagina": 20})
            registros_07, reintentos_07 = medir(
                cliente, total_07, ADOPTANTES_RNF07, HILOS
            )

    resumen_07, cumple_07 = resumen(
        "RNF-07 - escalabilidad con 2000 fichas y 5000 adoptantes",
        registros_07,
        total_07,
        UMBRAL_MS,
        criterio="p95",
        reintentos=reintentos_07,
    )
    lineas.extend(resumen_07)
    p95_07 = percentil95([registro[1] for registro in registros_07])
    lineas.extend(
        [
            "-" * 78,
            f"Umbral RNF-07: p95 <= {UMBRAL_MS:.0f} ms; medido p95 = {p95_07:.2f} ms.",
            "",
            "=" * 78,
            "RESULTADO FINAL: "
            + ("CUMPLE. RNF-05 y RNF-07 tienen evidencia reproducible." if cumple_05 and cumple_07
               else "NO CUMPLE. Revise los resultados anteriores."),
            "=" * 78,
        ]
    )

    texto = "\n".join(lineas) + "\n"
    SALIDA.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"Evidencia escrita en: {SALIDA}")
    return 0 if cumple_05 and cumple_07 else 1


if __name__ == "__main__":
    raise SystemExit(main())
