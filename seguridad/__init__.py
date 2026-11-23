# -*- coding: utf-8 -*-
"""Autenticación básica por rol del corte vertical (RF-05 y RF-34)."""

from seguridad.autenticacion import (
    CredencialesInvalidas,
    ErrorSeguridad,
    PropietarioNoAutorizado,
    RolNoAutorizado,
    TokenInvalido,
    crear_token,
    decodificar_token,
    hash_contrasena,
    obtener_secreto_jwt,
    requerir_roles,
    usuario_actual,
    verificar_contrasena,
    verificar_propietario,
)

__all__ = [
    "CredencialesInvalidas",
    "ErrorSeguridad",
    "PropietarioNoAutorizado",
    "RolNoAutorizado",
    "TokenInvalido",
    "crear_token",
    "decodificar_token",
    "hash_contrasena",
    "obtener_secreto_jwt",
    "requerir_roles",
    "usuario_actual",
    "verificar_contrasena",
    "verificar_propietario",
]
