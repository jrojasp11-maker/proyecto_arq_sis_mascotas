# -*- coding: utf-8 -*-
"""Matriz de entradas inválidas sobre la API (RNF-10: integridad).

Cada caso verifica que la API rechaza la petición y que no queda ninguna fila
nueva ni se modifica la ficha existente.
"""

from __future__ import annotations

import sqlite3

import pytest

from pruebas.conftest import contar, datos_mascota

CASOS_POST = [
    ("especie fuera de dominio", {"especie": "conejo"}, 400, "ERR-004"),
    ("tamano fuera de dominio", {"tamano": "gigante"}, 400, "ERR-004"),
    ("edad negativa", {"edad_meses": -1}, 400, "ERR-004"),
    ("nombre vacío", {"nombre": ""}, 400, "ERR-004"),
    ("campo obligatorio nulo", {"nombre": None}, 400, "ERR-004"),
    ("refugio inexistente", {"refugio_id": 999}, 404, "ERR-008"),
    ("refugio no verificado", {"refugio_id": 2}, 409, "ERR-009"),
    (
        "más de cinco fotografías",
        {"fotografias": [f"foto_{i}.jpg" for i in range(1, 7)]},
        400,
        "ERR-004",
    ),
    ("extensión no permitida", {"fotografias": ["foto.gif"]}, 400, "ERR-004"),
]


@pytest.mark.parametrize("nombre,cambios,estado,codigo", CASOS_POST)
def test_post_invalido_no_persiste(
    cliente, ruta_db, nombre, cambios, estado, codigo
):
    antes_mascotas = contar(ruta_db, "mascota")
    antes_fotos = contar(ruta_db, "fotografia")

    respuesta = cliente.post("/api/v1/mascotas", json=datos_mascota(**cambios))

    assert respuesta.status_code == estado, f"{nombre}: {respuesta.text}"
    assert respuesta.json()["codigo"] == codigo, nombre
    assert contar(ruta_db, "mascota") == antes_mascotas, nombre
    assert contar(ruta_db, "fotografia") == antes_fotos, nombre


@pytest.mark.parametrize(
    "cambios",
    [
        {"especie": "conejo"},
        {"fotografias": ["foto.gif"]},
        {"fecha_publicacion": "no-es-una-fecha"},
    ],
)
def test_put_invalido_no_modifica(cliente, ruta_db, cambios):
    antes_fotos = contar(ruta_db, "fotografia")

    respuesta = cliente.put(
        "/api/v1/mascotas/1", json={"refugio_id": 1, **cambios}
    )

    assert respuesta.status_code == 400, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-004"

    with sqlite3.connect(ruta_db) as conexion:
        fila = conexion.execute(
            "SELECT nombre, especie, fecha_publicacion FROM mascota WHERE id = 1"
        ).fetchone()
    assert fila == ("Luna", "perro", "2026-10-01")
    assert contar(ruta_db, "fotografia") == antes_fotos


def test_put_de_otro_refugio_no_modifica(cliente, ruta_db):
    respuesta = cliente.put(
        "/api/v1/mascotas/1", json={"refugio_id": 2, "nombre": "Intruso"}
    )

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-003"

    with sqlite3.connect(ruta_db) as conexion:
        nombre = conexion.execute(
            "SELECT nombre FROM mascota WHERE id = 1"
        ).fetchone()[0]
    assert nombre == "Luna"


def test_delete_de_otro_refugio_no_modifica(cliente, ruta_db):
    respuesta = cliente.delete("/api/v1/mascotas/1", params={"refugio_id": 2})

    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-003"

    with sqlite3.connect(ruta_db) as conexion:
        estado = conexion.execute(
            "SELECT estado FROM mascota WHERE id = 1"
        ).fetchone()[0]
    assert estado == "disponible"
