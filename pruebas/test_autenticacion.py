# -*- coding: utf-8 -*-
"""Pruebas de autenticación básica por rol y autorización de propietario."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from pruebas.conftest import CLAVE_DEMO, SECRETO_PRUEBAS, datos_mascota
from seguridad.autenticacion import hash_contrasena, verificar_contrasena


def test_login_devuelve_token_y_rol(cliente_sin_token):
    respuesta = cliente_sin_token.post(
        "/api/v1/auth/token",
        json={"usuario": "refugio", "contrasena": CLAVE_DEMO},
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["token_type"] == "bearer"
    assert datos["rol"] == "refugio"
    assert datos["refugio_id"] == 1
    assert datos["expires_in"] == 3600
    assert isinstance(datos["access_token"], str)


def test_login_contraseña_incorrecta_401(cliente_sin_token):
    respuesta = cliente_sin_token.post(
        "/api/v1/auth/token",
        json={"usuario": "refugio", "contrasena": "incorrecta123"},
    )

    assert respuesta.status_code == 401, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-401"


def test_sin_token_401(cliente_sin_token):
    assert cliente_sin_token.get("/api/v1/mascotas").status_code == 200
    respuesta = cliente_sin_token.post(
        "/api/v1/mascotas", json=datos_mascota()
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "ERR-401"


def test_token_invalido_401(cliente_sin_token):
    respuesta = cliente_sin_token.post(
        "/api/v1/mascotas",
        json=datos_mascota(),
        headers={"Authorization": "Bearer token-no-valido"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "ERR-401"


def test_token_expirado_401(cliente_sin_token):
    ahora = datetime.now(timezone.utc)
    expirado = jwt.encode(
        {
            "sub": "refugio",
            "rol": "refugio",
            "refugio_id": 1,
            "iat": ahora - timedelta(minutes=10),
            "exp": ahora - timedelta(minutes=5),
        },
        SECRETO_PRUEBAS,
        algorithm="HS256",
    )
    respuesta = cliente_sin_token.post(
        "/api/v1/mascotas",
        json=datos_mascota(),
        headers={"Authorization": f"Bearer {expirado}"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == "ERR-401"


def test_adoptante_solo_consulta_catalogo(cliente_adoptante):
    catalogo = cliente_adoptante.get("/api/v1/mascotas")
    assert catalogo.status_code == 200, catalogo.text

    creacion = cliente_adoptante.post(
        "/api/v1/mascotas", json=datos_mascota()
    )
    assert creacion.status_code == 403, creacion.text
    assert creacion.json()["codigo"] == "ERR-403"


def test_refugio_no_puede_operar_otro_refugio(cliente):
    respuesta = cliente.post(
        "/api/v1/mascotas", json=datos_mascota(refugio_id=2)
    )
    assert respuesta.status_code == 403, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-003"


def test_admin_puede_operar_cualquier_refugio(cliente_admin):
    respuesta = cliente_admin.post(
        "/api/v1/mascotas", json=datos_mascota(refugio_id=2)
    )
    # El token permite la operación; la regla de negocio rechaza el refugio 2.
    assert respuesta.status_code == 409, respuesta.text
    assert respuesta.json()["codigo"] == "ERR-009"


def test_hash_de_contraseña_no_es_reversible():
    guardado = hash_contrasena("Aqsis2026!")
    assert "Aqsis2026!" not in guardado
    assert verificar_contrasena("Aqsis2026!", guardado)
    assert not verificar_contrasena("otra-clave-123", guardado)
