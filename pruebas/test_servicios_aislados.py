# -*- coding: utf-8 -*-
"""Pruebas aisladas de los servicios con un doble del repositorio (RNF-08).

Ninguna prueba de este archivo abre una conexión real: el repositorio se
reemplaza por ``RepositorioFalso`` y se verifican las llamadas.
"""

from __future__ import annotations

import sqlite3

import pytest

from persistencia.repositorio import (
    DatosInvalidos,
    FichaNoEncontrada,
    RefugioNoVerificado,
)
from servicios.servicio_catalogo import ServicioCatalogo
from servicios.servicio_mascotas import ServicioMascotas


class RepositorioFalso:
    """Doble en memoria: devuelve hechos conocidos y registra las llamadas."""

    def __init__(self, ficha=None, error_crear=None, error_catalogo=None):
        self.ficha = ficha
        self.error_crear = error_crear
        self.error_catalogo = error_catalogo
        self.llamadas: list[tuple] = []

    def crear_ficha(self, refugio_id, ficha, fotografias=None):
        self.llamadas.append(
            ("crear_ficha", refugio_id, dict(ficha), list(fotografias or []))
        )
        if self.error_crear is not None:
            raise self.error_crear
        self.ficha = {
            "id": 99,
            "refugio_id": refugio_id,
            "estado": "disponible",
            **ficha,
            "fotografias": [
                {"id": indice, "archivo": archivo, "orden": indice}
                for indice, archivo in enumerate(fotografias or [], start=1)
            ],
        }
        return 99

    def obtener_por_id(self, mascota_id):
        self.llamadas.append(("obtener_por_id", mascota_id))
        return self.ficha

    def actualizar_ficha(self, mascota_id, refugio_id, cambios, fotografias=None):
        self.llamadas.append(
            (
                "actualizar_ficha",
                mascota_id,
                refugio_id,
                dict(cambios),
                fotografias,
            )
        )
        return {**(self.ficha or {}), **cambios, "id": mascota_id}

    def dar_de_baja(self, mascota_id, refugio_id):
        self.llamadas.append(("dar_de_baja", mascota_id, refugio_id))

    def listar_catalogo(
        self,
        especie=None,
        tamano=None,
        edad_min=None,
        edad_max=None,
        pagina=1,
        por_pagina=20,
    ):
        self.llamadas.append(
            (
                "listar_catalogo",
                {
                    "especie": especie,
                    "tamano": tamano,
                    "edad_min": edad_min,
                    "edad_max": edad_max,
                    "pagina": pagina,
                    "por_pagina": por_pagina,
                },
            )
        )
        if self.error_catalogo is not None:
            raise self.error_catalogo
        return {
            "total": 1,
            "pagina": pagina,
            "porPagina": por_pagina,
            "mascotas": [{"id": 1, "nombre": "Luna"}],
        }


FICHA_CONOCIDA = {
    "id": 7,
    "refugio_id": 1,
    "nombre": "Nala",
    "estado": "disponible",
    "fotografias": [],
}


def test_crear_valido_sin_base_real():
    repositorio = RepositorioFalso()
    servicio = ServicioMascotas(repositorio)

    ficha = servicio.crear(
        {
            "refugio_id": 1,
            "nombre": "Nala",
            "especie": "perro",
            "fotografias": ["nala_01.jpg"],
        }
    )

    assert ficha["id"] == 99
    assert ficha["estado"] == "disponible"
    assert [paso[0] for paso in repositorio.llamadas] == [
        "crear_ficha",
        "obtener_por_id",
    ]
    assert repositorio.llamadas[0][2]["nombre"] == "Nala"
    assert repositorio.llamadas[0][3] == ["nala_01.jpg"]


def test_crear_rechazado_no_consulta_ni_guarda():
    repositorio = RepositorioFalso(error_crear=RefugioNoVerificado(2))
    servicio = ServicioMascotas(repositorio)

    with pytest.raises(RefugioNoVerificado) as error:
        servicio.crear({"refugio_id": 2, "nombre": "Nala", "fotografias": []})

    assert error.value.codigo == "ERR-009"
    assert [paso[0] for paso in repositorio.llamadas] == ["crear_ficha"]


def test_consultar_existente_solo_lee():
    repositorio = RepositorioFalso(ficha=dict(FICHA_CONOCIDA))
    servicio = ServicioMascotas(repositorio)

    ficha = servicio.consultar(7)

    assert ficha["nombre"] == "Nala"
    assert [paso[0] for paso in repositorio.llamadas] == ["obtener_por_id"]


def test_consultar_ausente_lanza_error_controlado():
    repositorio = RepositorioFalso(ficha=None)
    servicio = ServicioMascotas(repositorio)

    with pytest.raises(FichaNoEncontrada) as error:
        servicio.consultar(99999)

    assert error.value.codigo == "ERR-011"
    assert [paso[0] for paso in repositorio.llamadas] == ["obtener_por_id"]


def test_actualizar_delega_en_repositorio():
    repositorio = RepositorioFalso(ficha=dict(FICHA_CONOCIDA))
    servicio = ServicioMascotas(repositorio)

    ficha = servicio.actualizar(
        7, {"refugio_id": 1, "nombre": "Nala II", "fotografias": ["n.jpg"]}
    )

    assert ficha["nombre"] == "Nala II"
    llamada = repositorio.llamadas[0]
    assert llamada[0] == "actualizar_ficha"
    assert llamada[1:3] == (7, 1)
    assert llamada[3] == {"nombre": "Nala II"}
    assert llamada[4] == ["n.jpg"]


def test_dar_de_baja_delega_en_repositorio():
    repositorio = RepositorioFalso(ficha=dict(FICHA_CONOCIDA))
    servicio = ServicioMascotas(repositorio)

    servicio.dar_de_baja(7, 1)

    assert repositorio.llamadas == [("dar_de_baja", 7, 1)]


def test_catalogo_normaliza_snake_case_y_delega():
    repositorio = RepositorioFalso()
    servicio = ServicioCatalogo(repositorio)

    pagina = servicio.listar(especie="perro", pagina=2, por_pagina=10)

    assert pagina["por_pagina"] == 10
    assert "porPagina" not in pagina
    assert pagina["mascotas"][0]["nombre"] == "Luna"
    llamada = repositorio.llamadas[0]
    assert llamada[0] == "listar_catalogo"
    assert llamada[1]["especie"] == "perro"
    assert llamada[1]["pagina"] == 2
    assert llamada[1]["por_pagina"] == 10


def test_catalogo_rechaza_filtro_invalido():
    repositorio = RepositorioFalso(error_catalogo=DatosInvalidos("especie inválida"))
    servicio = ServicioCatalogo(repositorio)

    with pytest.raises(DatosInvalidos):
        servicio.listar(especie="conejo")

    assert [paso[0] for paso in repositorio.llamadas] == ["listar_catalogo"]


def test_servicios_no_abren_conexion_real(monkeypatch):
    def conexion_prohibida(*args, **kwargs):
        raise AssertionError("el servicio abrió una conexión real")

    monkeypatch.setattr(sqlite3, "connect", conexion_prohibida)

    repositorio = RepositorioFalso(ficha=dict(FICHA_CONOCIDA))
    servicio = ServicioMascotas(repositorio)
    catalogo = ServicioCatalogo(repositorio)

    servicio.crear({"refugio_id": 1, "nombre": "Nala", "fotografias": []})
    servicio.consultar(7)
    servicio.actualizar(7, {"refugio_id": 1, "nombre": "Nala II"})
    servicio.dar_de_baja(7, 1)
    catalogo.listar(especie="perro")
