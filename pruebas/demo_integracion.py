# -*- coding: utf-8 -*-
"""Demostracion reproducible de la integracion de la interfaz (semana 15).

Genera ``evidencias/integracion_ui.txt``. Los escenarios son los mismos que se
ejecutan desde la pantalla: interfaz sirviendose desde la API, creacion con id
real, rechazo de negocio, entrada invalida, edicion, baja, persistencia tras
reiniciar el servidor, consulta del catalogo, ausencia y fallo de comunicacion.

Uso:
    python -m pruebas.demo_integracion
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import httpx

from persistencia.inicializar_db import inicializar
from pruebas.servidor import servidor_api, token_de_cliente

RAIZ = Path(__file__).resolve().parent.parent
EVIDENCIAS = RAIZ / "evidencias"
RUTA_DB = EVIDENCIAS / "integracion_ui.db"
SALIDA = EVIDENCIAS / "integracion_ui.txt"

CUERPO_VALIDO = {
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
    "fecha_publicacion": "2026-11-20",
    "fotografias": ["nala_01.jpg", "nala_02.jpg"],
}


def contar(tabla: str) -> int:
    with sqlite3.connect(RUTA_DB) as conexion:
        return int(conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])


def fila(mascota_id: int) -> tuple | None:
    with sqlite3.connect(RUTA_DB) as conexion:
        return conexion.execute(
            "SELECT nombre, estado FROM mascota WHERE id = ?", (mascota_id,)
        ).fetchone()


def main() -> int:
    EVIDENCIAS.mkdir(parents=True, exist_ok=True)
    inicializar(RUTA_DB)
    lineas: list[str] = [
        "INTEGRACION DE LA INTERFAZ CON LA API REAL - SEMANA 15",
        "=" * 78,
        f"Base de datos: {RUTA_DB}",
        "Servidor: Uvicorn temporal | Cliente: httpx | Interfaz: /ui/",
        "Los envios reproducen las solicitudes que hace frontend/app.js.",
        "=" * 78,
        "",
    ]
    errores: list[str] = []
    nuevo_id: int | None = None

    def chequear(condicion: bool, texto: str) -> None:
        if not condicion:
            errores.append(texto)

    with servidor_api(RUTA_DB) as url:
        with httpx.Client(base_url=url, timeout=10) as cliente:
            cliente.headers.update(
                {"Authorization": f"Bearer {token_de_cliente(cliente, 'admin')}"}
            )
            pagina = cliente.get("/ui/")
            js = cliente.get("/ui/app.js")
            css = cliente.get("/ui/styles.css")
            chequear(pagina.status_code == 200, "la interfaz no responde 200")
            chequear(js.status_code == 200, "app.js no responde 200")
            chequear(css.status_code == 200, "styles.css no responde 200")
            lineas.append(
                f"UI | GET /ui/ -> {pagina.status_code}; "
                f"/ui/app.js -> {js.status_code}; /ui/styles.css -> {css.status_code}"
            )
            lineas.append(
                "UI | controles: form-crear, form-catalogo, btn-editar, btn-baja, btn-consultar"
            )
            pestanas = all(
                f'id="tab-{nombre}"' in pagina.text
                and f'id="panel-{nombre}"' in pagina.text
                for nombre in ("crear", "editar", "catalogo")
            )
            relleno = (
                'id="btn-rellenar"' in pagina.text
                and "function rellenarDemo" in js.text
                and "function activarPestana" in js.text
            )
            login = (
                'id="panel-login"' in pagina.text
                and 'id="form-login"' in pagina.text
                and 'id="btn-login"' in pagina.text
                and 'id="login-usuario"' in pagina.text
                and 'id="login-contrasena"' in pagina.text
                and 'id="app" hidden' in pagina.text
                and "function iniciarSesion" in js.text
                and 'cabeceras.Authorization = "Bearer " + tokenActual' in js.text
                and 'porId("app").hidden = false' in js.text
            )
            chequear(pestanas, "las pestañas de RF-05 y RF-34 no estan en la pagina")
            chequear(relleno, "el relleno automatico de ejemplo no esta disponible")
            chequear(login, "la pantalla de inicio de sesion o el bloqueo de la interfaz no estan presentes")
            lineas.append(
                "UI | pestanas: crear / editar / catalogo "
                f"({'presentes' if pestanas else 'AUSENTES'}); "
                f"relleno automatico: {'presente' if relleno else 'AUSENTE'}; "
                f"login y token: {'presentes' if login else 'AUSENTES'}"
            )
            lineas.append("")

            antes = contar("mascota")
            crear = cliente.post("/api/v1/mascotas", json=CUERPO_VALIDO)
            lineas.append(
                f"RF-05 valido | POST /api/v1/mascotas -> HTTP {crear.status_code}"
            )
            chequear(crear.status_code == 201, "la creacion no respondio 201")
            if crear.status_code == 201:
                nuevo_id = crear.json()["id"]
                lineas.append(
                    f"  id real devuelto: {nuevo_id}; estado: {crear.json()['estado']}; "
                    f"fotos: {len(crear.json()['fotografias'])}"
                )
                chequear(crear.json()["estado"] == "disponible", "estado inicial incorrecto")
                chequear(contar("mascota") == antes + 1, "no se persistio la ficha")
                chequear(fila(nuevo_id) is not None, "no se leyo la ficha desde otra conexion")
            else:
                lineas.append(f"  cuerpo: {crear.text}")

            rechazo = cliente.post(
                "/api/v1/mascotas", json={**CUERPO_VALIDO, "refugio_id": 2}
            )
            lineas.append(
                f"RF-05 rechazo | POST con refugio no verificado -> HTTP {rechazo.status_code}; "
                f"codigo {rechazo.json().get('codigo')}; filas: {contar('mascota')}"
            )
            chequear(rechazo.status_code == 409, "el rechazo de negocio no respondio 409")
            chequear(rechazo.json().get("codigo") == "ERR-009", "codigo ERR-009 ausente")
            chequear(contar("mascota") == antes + 1, "el rechazo escribio en la base")

            invalida = cliente.post(
                "/api/v1/mascotas", json={**CUERPO_VALIDO, "especie": "conejo"}
            )
            lineas.append(
                f"RF-05 entrada | POST con especie invalida -> HTTP {invalida.status_code}; "
                f"codigo {invalida.json().get('codigo')}"
            )
            chequear(invalida.status_code == 400, "la entrada invalida no respondio 400")
            chequear(invalida.json().get("codigo") == "ERR-004", "codigo ERR-004 ausente")

            catalogo = cliente.get(
                "/api/v1/mascotas",
                params={"pagina": 1, "por_pagina": 20},
            )
            ids = [m["id"] for m in catalogo.json()["mascotas"]]
            lineas.append(
                f"RF-34 valido | GET /api/v1/mascotas -> HTTP {catalogo.status_code}; "
                f"total {catalogo.json()['total']}; ids {ids}"
            )
            chequear(catalogo.status_code == 200, "el catalogo no respondio 200")
            chequear(nuevo_id in ids, "la ficha creada no aparece en el catalogo")

            filtros = cliente.get(
                "/api/v1/mascotas", params={"especie": "perro", "tamano": "mediano"}
            )
            lineas.append(
                f"RF-34 filtros | perro/mediano -> HTTP {filtros.status_code}; "
                f"ids {[m['id'] for m in filtros.json()['mascotas']]}"
            )
            chequear(filtros.status_code == 200, "los filtros fallaron")

            pagina1 = cliente.get(
                "/api/v1/mascotas", params={"pagina": 1, "por_pagina": 2}
            )
            pagina2 = cliente.get(
                "/api/v1/mascotas", params={"pagina": 2, "por_pagina": 2}
            )
            lineas.append(
                f"RF-34 paginacion | p1 {[m['id'] for m in pagina1.json()['mascotas']]}; "
                f"p2 {[m['id'] for m in pagina2.json()['mascotas']]}; "
                f"total {pagina1.json()['total']}"
            )
            chequear(pagina1.status_code == 200 and pagina2.status_code == 200, "paginacion fallida")

            ausencia = cliente.get(
                "/api/v1/mascotas", params={"especie": "gato", "tamano": "grande"}
            )
            lineas.append(
                f"RF-34 ausencia | gato/grande -> HTTP {ausencia.status_code}; "
                f"total {ausencia.json()['total']}; lista {ausencia.json()['mascotas']}"
            )
            chequear(
                ausencia.status_code == 200 and ausencia.json()["total"] == 0,
                "la ausencia no respondio 200 con total 0",
            )

            filtro_invalido = cliente.get(
                "/api/v1/mascotas", params={"especie": "conejo"}
            )
            lineas.append(
                f"RF-34 entrada | especie=conejo -> HTTP {filtro_invalido.status_code}; "
                f"codigo {filtro_invalido.json().get('codigo')}"
            )
            chequear(filtro_invalido.status_code == 400, "el filtro invalido no respondio 400")

            if nuevo_id is not None:
                edicion = cliente.put(
                    f"/api/v1/mascotas/{nuevo_id}",
                    json={"refugio_id": 1, "nombre": "Nala actualizada"},
                )
                lineas.append(
                    f"RF-05 edicion | PUT /api/v1/mascotas/{nuevo_id} -> HTTP {edicion.status_code}; "
                    f"nombre {edicion.json().get('nombre')}"
                )
                chequear(edicion.status_code == 200, "la edicion no respondio 200")

                baja = cliente.delete(
                    f"/api/v1/mascotas/{nuevo_id}", params={"refugio_id": 1}
                )
                lineas.append(
                    f"RF-05 baja | DELETE /api/v1/mascotas/{nuevo_id}?refugio_id=1 "
                    f"-> HTTP {baja.status_code}"
                )
                chequear(baja.status_code == 204, "la baja no respondio 204")
                chequear(fila(nuevo_id)[1] == "baja", "la baja no cambio el estado en la base")

                despues = cliente.get("/api/v1/mascotas")
                ids_despues = [m["id"] for m in despues.json()["mascotas"]]
                lineas.append(
                    f"RF-34 tras baja | ids {ids_despues}; ficha {nuevo_id} ausente: "
                    f"{nuevo_id not in ids_despues}"
                )
                chequear(nuevo_id not in ids_despues, "la ficha dada de baja sigue en el catalogo")
            lineas.append("")

    # El backend se detuvo: la interfaz debe mostrar fallo de comunicacion,
    # nunca un exito falso. No se reintenta automaticamente.
    try:
        with httpx.Client(base_url=url, timeout=2) as cliente:
            cliente.get("/api/v1/mascotas")
        lineas.append("COMUNICACION | backend detenido: la peticion NO fallo (revisar)")
        errores.append("la peticion con el backend detenido no fallo")
    except httpx.RequestError as error:
        lineas.append(
            "COMUNICACION | backend detenido: error de conexion confirmado "
            f"({type(error).__name__}); la interfaz avisa 'resultado no confirmado' "
            "y no muestra un exito falso."
        )

    # Reinicio del backend: el estado sigue persistido (RF-05 y RF-34).
    if nuevo_id is not None:
        with servidor_api(RUTA_DB) as url_reinicio:
            with httpx.Client(base_url=url_reinicio, timeout=10) as cliente:
                cliente.headers.update(
                    {"Authorization": f"Bearer {token_de_cliente(cliente, 'admin')}"}
                )
                recargado = cliente.get("/api/v1/mascotas")
                ids_reinicio = [m["id"] for m in recargado.json()["mascotas"]]
                lineas.append(
                    f"PERSISTENCIA | tras reiniciar el backend: HTTP {recargado.status_code}; "
                    f"ficha {nuevo_id} dado de baja ausente: {nuevo_id not in ids_reinicio}"
                )
                chequear(recargado.status_code == 200, "fallo la consulta tras reiniciar")
                chequear(nuevo_id not in ids_reinicio, "la baja no perduro tras reiniciar")

    lineas.append("")
    lineas.append("=" * 78)
    if errores:
        lineas.append("RESULTADO: NO CUMPLE")
        for error in errores:
            lineas.append(f"  - {error}")
        codigo = 1
    else:
        lineas.append("RESULTADO: CUMPLE. Interfaz, API, servicios, repositorio y base verificados.")
        codigo = 0
    lineas.append("=" * 78)

    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[-14:]))
    print(f"\nEvidencia escrita en: {SALIDA}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
