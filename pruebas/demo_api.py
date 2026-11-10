# -*- coding: utf-8 -*-
"""Demostración de ambos RF con un cliente HTTP real.

Genera ``evidencias/demo_api.txt`` con las peticiones y respuestas de:
crear (RF-05), consultar catálogo (RF-34), actualizar (RF-05), dar de baja
(RF-05), catálogo vacío y filtro inválido.

Uso:
    python -m pruebas.demo_api
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

from persistencia.inicializar_db import inicializar
from pruebas.servidor import servidor_api

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"
RUTA_DB = EVIDENCIAS / "demo_api.db"
SALIDA = EVIDENCIAS / "demo_api.txt"

CUERPO_CREAR = {
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
    "fecha_publicacion": "2026-11-10",
    "fotografias": ["nala_01.jpg", "nala_02.jpg"],
}


def registrar(lineas, titulo, respuesta, peticion=None):
    lineas.append("=" * 78)
    lineas.append(titulo)
    if peticion is not None:
        lineas.append("Solicitud:")
        lineas.append(json.dumps(peticion, ensure_ascii=False, indent=2))
    lineas.append(f"HTTP {respuesta.status_code}")
    try:
        cuerpo = respuesta.json()
    except ValueError:
        lineas.append("(sin cuerpo)")
    else:
        lineas.append(json.dumps(cuerpo, ensure_ascii=False, indent=2))
    lineas.append("")


def main() -> int:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    ruta = inicializar(RUTA_DB)
    lineas: list[str] = [
        "DEMOSTRACIÓN HTTP DE RF-05 Y RF-34",
        "=" * 78,
        f"Base de datos: {ruta}",
        "Cliente: httpx | Servidor: Uvicorn | API: http://127.0.0.1:<puerto>/api/v1",
        "=" * 78,
        "",
    ]
    errores: list[str] = []

    with servidor_api(ruta) as url_base:
        with httpx.Client(base_url=url_base, timeout=10) as cliente:
            crear = cliente.post("/api/v1/mascotas", json=CUERPO_CREAR)
            registrar(
                lineas,
                "RF-05 | POST /api/v1/mascotas",
                crear,
                CUERPO_CREAR,
            )
            if crear.status_code != 201:
                errores.append(f"POST respondió {crear.status_code}")
                nuevo_id = None
            else:
                nuevo_id = crear.json()["id"]

            filtros = {"especie": "perro", "tamano": "mediano"}
            catalogo = cliente.get("/api/v1/mascotas", params=filtros)
            registrar(
                lineas,
                f"RF-34 | GET /api/v1/mascotas?especie=perro&tamano=mediano",
                catalogo,
            )
            if catalogo.status_code != 200:
                errores.append(f"GET catálogo respondió {catalogo.status_code}")

            if nuevo_id is not None:
                cambios = {
                    "refugio_id": 1,
                    "nombre": "Nala actualizada",
                    "fotografias": ["nala_01.jpg"],
                }
                actualizar = cliente.put(
                    f"/api/v1/mascotas/{nuevo_id}", json=cambios
                )
                registrar(
                    lineas,
                    f"RF-05 | PUT /api/v1/mascotas/{nuevo_id}",
                    actualizar,
                    cambios,
                )
                if actualizar.status_code != 200:
                    errores.append(
                        f"PUT respondió {actualizar.status_code}"
                    )

                baja = cliente.delete(
                    f"/api/v1/mascotas/{nuevo_id}", params={"refugio_id": 1}
                )
                registrar(
                    lineas,
                    f"RF-05 | DELETE /api/v1/mascotas/{nuevo_id}?refugio_id=1",
                    baja,
                )
                if baja.status_code != 204:
                    errores.append(f"DELETE respondió {baja.status_code}")

                despues = cliente.get("/api/v1/mascotas", params=filtros)
                registrar(
                    lineas,
                    "RF-34 | GET catálogo después de la baja (Nala no debe aparecer)",
                    despues,
                )
                ids = [m["id"] for m in despues.json().get("mascotas", [])]
                if nuevo_id in ids:
                    errores.append("la ficha dada de baja sigue en el catálogo")

            vacio = cliente.get(
                "/api/v1/mascotas",
                params={"especie": "gato", "tamano": "grande"},
            )
            registrar(
                lineas,
                "RF-34 | GET catálogo sin coincidencias (condición límite)",
                vacio,
            )
            if vacio.status_code != 200 or vacio.json().get("total") != 0:
                errores.append("el catálogo vacío no respondió 200 con total 0")

            invalido = cliente.get(
                "/api/v1/mascotas", params={"especie": "conejo"}
            )
            registrar(
                lineas,
                "RF-34 | GET catálogo con filtro inválido",
                invalido,
            )
            if invalido.status_code != 400:
                errores.append(
                    f"el filtro inválido respondió {invalido.status_code}"
                )

    lineas.append("=" * 78)
    if errores:
        lineas.append("RESULTADO: NO CUMPLE")
        for error in errores:
            lineas.append(f"  - {error}")
        codigo = 1
    else:
        lineas.append("RESULTADO: CUMPLE. Ambos RF responden según el contrato.")
        codigo = 0
    lineas.append("=" * 78)

    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[-12:]))
    print(f"\nEvidencia escrita en: {SALIDA}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
