# -*- coding: utf-8 -*-
"""Pruebas funcionales del RF-05 a través de la API."""

from __future__ import annotations

import sqlite3

from pruebas.conftest import contar, datos_mascota


def test_crear_ficha_valida_201(cliente, ruta_db):
    respuesta = cliente.post("/api/v1/mascotas", json=datos_mascota())
    assert respuesta.status_code == 201, respuesta.text

    ficha = respuesta.json()
    assert ficha["id"] == 7
    assert ficha["nombre"] == "Nala"
    assert ficha["estado"] == "disponible"
    assert ficha["refugio_nombre"] == "Refugio Patitas"
    assert [foto["archivo"] for foto in ficha["fotografias"]] == [
        "nala_01.jpg",
        "nala_02.jpg",
    ]

    # Persistencia real: se verifica desde otra conexión.
    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT nombre, estado FROM mascota WHERE id = ?", (ficha["id"],)
        ).fetchone()
        fotos = conexion.execute(
            "SELECT COUNT(*) FROM fotografia WHERE mascota_id = ?", (ficha["id"],)
        ).fetchone()[0]
    assert fila == ("Nala", "disponible")
    assert fotos == 2

    # RF-34: la ficha recién creada ya aparece en el catálogo.
    catalogo = cliente.get(
        "/api/v1/mascotas", params={"especie": "perro", "tamano": "mediano"}
    )
    assert catalogo.status_code == 200
    assert ficha["id"] in [m["id"] for m in catalogo.json()["mascotas"]]


def test_crear_refugio_no_verificado_409(cliente, ruta_db):
    antes_mascotas = contar(ruta_db, "mascota")
    antes_fotos = contar(ruta_db, "fotografia")

    respuesta = cliente.post(
        "/api/v1/mascotas", json=datos_mascota(refugio_id=2)
    )

    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-009"
    assert contar(ruta_db, "mascota") == antes_mascotas
    assert contar(ruta_db, "fotografia") == antes_fotos


def test_crear_datos_invalidos_400(cliente, ruta_db):
    antes = contar(ruta_db, "mascota")

    respuesta = cliente.post(
        "/api/v1/mascotas", json=datos_mascota(especie="conejo")
    )

    assert respuesta.status_code == 400, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-004"
    assert contar(ruta_db, "mascota") == antes


def test_actualizar_ficha_200(cliente, ruta_db):
    respuesta = cliente.put(
        "/api/v1/mascotas/5",
        json={
            "refugio_id": 1,
            "nombre": "Toby actualizado",
            "fotografias": ["toby_01.jpg"],
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    ficha = respuesta.json()
    assert ficha["nombre"] == "Toby actualizado"
    assert ficha["estado"] == "disponible"
    assert [foto["archivo"] for foto in ficha["fotografias"]] == ["toby_01.jpg"]

    catalogo = cliente.get("/api/v1/mascotas")
    ids = [m["id"] for m in catalogo.json()["mascotas"]]
    assert 5 in ids


def test_actualizar_ficha_inexistente_404(cliente):
    respuesta = cliente.put(
        "/api/v1/mascotas/99999", json={"refugio_id": 1, "nombre": "Fantasma"}
    )

    assert respuesta.status_code == 404, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-011"


def test_actualizar_ficha_de_otro_refugio_403(cliente):
    respuesta = cliente.put(
        "/api/v1/mascotas/1", json={"refugio_id": 2, "nombre": "Intruso"}
    )

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-003"


def test_dar_de_baja_204(cliente, ruta_db):
    respuesta = cliente.delete(
        "/api/v1/mascotas/1", params={"refugio_id": 1}
    )

    assert respuesta.status_code == 204, respuesta.text
    assert respuesta.content == b""

    with sqlite3.connect(ruta_db) as conexion:
        estado = conexion.execute(
            "SELECT estado FROM mascota WHERE id = 1"
        ).fetchone()[0]
    assert estado == "baja"

    catalogo = cliente.get("/api/v1/mascotas")
    ids = [m["id"] for m in catalogo.json()["mascotas"]]
    assert 1 not in ids


def test_dar_de_baja_inexistente_404(cliente):
    respuesta = cliente.delete(
        "/api/v1/mascotas/99999", params={"refugio_id": 1}
    )

    assert respuesta.status_code == 404, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-011"
