# -*- coding: utf-8 -*-
"""Integracion de la interfaz con los contratos reales (semana 15).

La interfaz se sirve desde la propia API, en el mismo origen. Estas pruebas
comprueban que los archivos estan disponibles, que la pagina usa las claves del
contrato y que el recorrido de cada RF produce datos persistidos.
"""

from __future__ import annotations

import sqlite3

from pruebas.conftest import contar, datos_mascota


def test_interfaz_se_sirve_desde_la_api(cliente):
    inicio = cliente.get("/")
    assert inicio.status_code == 200
    assert inicio.json()["interfaz"] == "/ui/"

    pagina = cliente.get("/ui/")
    assert pagina.status_code == 200
    assert "form-crear" in pagina.text
    assert "form-catalogo" in pagina.text
    assert "/ui/styles.css" in pagina.text
    assert "/ui/app.js" in pagina.text

    assert cliente.get("/ui/styles.css").status_code == 200
    javascript = cliente.get("/ui/app.js")
    assert javascript.status_code == 200
    assert 'BASE = "/api/v1"' in javascript.text
    assert '+ "/mascotas"' in javascript.text


def test_interfaz_muestra_controles_estados_y_mensajes(cliente):
    pagina = cliente.get("/ui/").text
    for control in ("btn-crear", "btn-editar", "btn-baja", "btn-consultar"):
        assert 'id="' + control + '"' in pagina
    assert "aria-live" in pagina
    assert "role=\"status\"" in pagina
    assert "Fotografías (nombres separados por coma; 0 a 5)" in pagina

    # Organizacion por pestañas y relleno automatico de ejemplo.
    assert 'role="tablist"' in pagina
    for pestana in ("tab-crear", "tab-editar", "tab-catalogo"):
        assert 'id="' + pestana + '"' in pagina
    for panel in ("panel-crear", "panel-editar", "panel-catalogo"):
        assert 'id="' + panel + '"' in pagina
    assert 'id="btn-rellenar"' in pagina
    assert "Rellenar datos de ejemplo" in pagina

    javascript = cliente.get("/ui/app.js").text
    for texto in (
        "Enviando...", "Consultando...", "rechazo HTTP",
        "no se pudo contactar", "el servidor no esta disponible",
        "function activarPestana", "function rellenarDemo", "btn-rellenar",
    ):
        assert texto in javascript


def test_recorrido_completo_rf05_y_rf34(cliente, ruta_db):
    # La interfaz envia exactamente este cuerpo a POST /api/v1/mascotas.
    creacion = cliente.post("/api/v1/mascotas", json=datos_mascota())
    assert creacion.status_code == 201, creacion.text
    ficha = creacion.json()
    assert ficha["id"] == 7
    assert ficha["estado"] == "disponible"

    # Recarga de pagina: se consulta de nuevo y el id aparece desde la base.
    catalogo = cliente.get(
        "/api/v1/mascotas",
        params={"especie": "perro", "tamano": "mediano", "pagina": 1, "por_pagina": 20},
    )
    assert catalogo.status_code == 200
    assert ficha["id"] in [m["id"] for m in catalogo.json()["mascotas"]]

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT nombre, estado FROM mascota WHERE id = ?", (ficha["id"],)
        ).fetchone()
    assert fila == ("Nala", "disponible")

    # RF-05 edita y da de baja con el id devuelto por la API.
    edicion = cliente.put(
        "/api/v1/mascotas/7", json={"refugio_id": 1, "nombre": "Nala actualizada"}
    )
    assert edicion.status_code == 200, edicion.text
    assert edicion.json()["nombre"] == "Nala actualizada"

    baja = cliente.delete("/api/v1/mascotas/7", params={"refugio_id": 1})
    assert baja.status_code == 204

    final = cliente.get("/api/v1/mascotas")
    assert final.status_code == 200
    assert 7 not in [m["id"] for m in final.json()["mascotas"]]


def test_rechazo_ausencia_y_entrada_invalida(cliente, ruta_db):
    antes = contar(ruta_db, "mascota")

    rechazo = cliente.post("/api/v1/mascotas", json=datos_mascota(refugio_id=2))
    assert rechazo.status_code == 409
    assert rechazo.json()["codigo"] == "ERR-009"
    assert contar(ruta_db, "mascota") == antes

    invalida = cliente.get("/api/v1/mascotas", params={"especie": "conejo"})
    assert invalida.status_code == 400
    assert invalida.json()["codigo"] == "ERR-004"

    ausencia = cliente.get(
        "/api/v1/mascotas", params={"especie": "gato", "tamano": "grande"}
    )
    assert ausencia.status_code == 200
    assert ausencia.json()["total"] == 0
    assert ausencia.json()["mascotas"] == []


def test_claves_del_contrato_coinciden_con_la_interfaz(cliente):
    javascript = cliente.get("/ui/app.js").text
    respuesta = cliente.get("/api/v1/mascotas").json()
    for clave in ("total", "pagina", "por_pagina", "mascotas"):
        assert clave in respuesta
        assert clave in javascript

    assert "por_pagina" in javascript
    assert "edad_min" in javascript
    assert "edad_max" in javascript
