# -*- coding: utf-8 -*-
"""Pruebas funcionales del RF-34 a través de la API."""

from __future__ import annotations

CAMPOS_PERSONALES = {
    "correo",
    "telefono",
    "documento",
    "direccion",
    "nombre_completo",
    "nombreCompleto",
    "adoptante",
}


def test_catalogo_inicial_200(cliente):
    respuesta = cliente.get("/api/v1/mascotas")
    assert respuesta.status_code == 200, respuesta.text

    pagina = respuesta.json()
    assert pagina["total"] == 3
    assert pagina["pagina"] == 1
    assert pagina["por_pagina"] == 20
    assert [m["id"] for m in pagina["mascotas"]] == [1, 3, 2]
    assert all(m["foto_principal"] for m in pagina["mascotas"])


def test_catalogo_filtros(cliente):
    perros = cliente.get("/api/v1/mascotas", params={"especie": "perro"}).json()
    assert [m["id"] for m in perros["mascotas"]] == [1, 3]

    pequenos = cliente.get("/api/v1/mascotas", params={"tamano": "pequeno"}).json()
    assert [m["id"] for m in pequenos["mascotas"]] == [2]

    jovenes = cliente.get(
        "/api/v1/mascotas", params={"edad_min": 0, "edad_max": 20}
    ).json()
    assert [m["id"] for m in jovenes["mascotas"]] == [2]


def test_catalogo_paginacion(cliente):
    pagina_1 = cliente.get(
        "/api/v1/mascotas", params={"pagina": 1, "por_pagina": 2}
    ).json()
    pagina_2 = cliente.get(
        "/api/v1/mascotas", params={"pagina": 2, "por_pagina": 2}
    ).json()

    assert pagina_1["total"] == 3
    assert [m["id"] for m in pagina_1["mascotas"]] == [1, 3]
    assert [m["id"] for m in pagina_2["mascotas"]] == [2]


def test_catalogo_sin_resultados_200(cliente):
    """Condición límite: filtro válido sin coincidencias."""
    respuesta = cliente.get(
        "/api/v1/mascotas", params={"especie": "gato", "tamano": "grande"}
    )

    assert respuesta.status_code == 200, respuesta.text
    pagina = respuesta.json()
    assert pagina["total"] == 0
    assert pagina["mascotas"] == []


def test_catalogo_filtro_invalido_400(cliente):
    respuesta = cliente.get("/api/v1/mascotas", params={"especie": "conejo"})
    assert respuesta.status_code == 400, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-004"


def test_catalogo_pagina_invalida_400(cliente):
    respuesta = cliente.get("/api/v1/mascotas", params={"pagina": 0})
    assert respuesta.status_code == 400, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-004"


def test_catalogo_rango_de_edad_invertido_400(cliente):
    respuesta = cliente.get(
        "/api/v1/mascotas", params={"edad_min": 60, "edad_max": 12}
    )
    assert respuesta.status_code == 400, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-004"


def test_catalogo_sin_datos_personales_rnf04(cliente):
    pagina = cliente.get("/api/v1/mascotas").json()
    claves = set().union(*(m.keys() for m in pagina["mascotas"]))
    assert not (claves & CAMPOS_PERSONALES), claves & CAMPOS_PERSONALES
