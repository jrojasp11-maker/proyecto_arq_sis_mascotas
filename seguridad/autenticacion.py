# -*- coding: utf-8 -*-
"""JWT HS256 y autorización por rol para la API del corte vertical.

Los roles son ``refugio``, ``adoptante`` y ``admin``. Las contraseñas se
guardan con PBKDF2-HMAC-SHA256 y sal aleatoria; nunca se almacenan en claro.
El secreto de firma se lee de ``AUTH_JWT_SECRET``. En desarrollo local, si la
variable no existe, se usa un valor fijo solo para que las pruebas sean
reproducibles; con ``DATABASE_URL`` o ``VERCEL`` la variable es obligatoria.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ROLES = {"refugio", "adoptante", "admin"}
ALGORITMO = "HS256"
HASH_ALGORITMO = "pbkdf2_sha256"
ITERACIONES = 200_000
MINUTOS_TOKEN = 60
SECRETO_DESARROLLO = "aqsis-secreto-local-pruebas-no-produccion"

portador = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer",
    description="Token JWT devuelto por POST /api/v1/auth/token",
)


class ErrorSeguridad(Exception):
    """Error controlado de autenticación o autorización."""

    def __init__(self, codigo: str, mensaje: str):
        super().__init__(f"{codigo}: {mensaje}")
        self.codigo = codigo
        self.mensaje = mensaje


class CredencialesInvalidas(ErrorSeguridad):
    def __init__(self) -> None:
        super().__init__("ERR-401", "credenciales invalidas o ausentes")


class TokenInvalido(CredencialesInvalidas):
    def __init__(self, motivo: str = "token invalido o expirado") -> None:
        super().__init__()
        self.mensaje = motivo


class RolNoAutorizado(ErrorSeguridad):
    def __init__(self, rol: str) -> None:
        super().__init__("ERR-403", f"el rol {rol} no puede ejecutar esta operacion")


class PropietarioNoAutorizado(ErrorSeguridad):
    def __init__(self, refugio_id: int) -> None:
        super().__init__(
            "ERR-003", f"la ficha no pertenece al refugio {refugio_id} del token"
        )


def hash_contrasena(contrasena: str) -> str:
    """Devuelve una contraseña hasheada con sal aleatoria."""
    if not isinstance(contrasena, str) or len(contrasena) < 8:
        raise ValueError("la contraseña debe tener al menos 8 caracteres")
    sal = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode("utf-8"), sal, ITERACIONES
    )
    return f"{HASH_ALGORITMO}${ITERACIONES}${sal.hex()}${digest.hex()}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    """Compara una contraseña con un hash generado por :func:`hash_contrasena`."""
    try:
        algoritmo, iteraciones_txt, sal_hex, digest_hex = guardado.split("$")
        if algoritmo != HASH_ALGORITMO:
            return False
        sal = bytes.fromhex(sal_hex)
        esperado = bytes.fromhex(digest_hex)
        calculado = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode("utf-8"), sal, int(iteraciones_txt)
        )
    except (ValueError, AttributeError, TypeError):
        return False
    return hmac.compare_digest(calculado, esperado)


def obtener_secreto_jwt() -> str:
    """Lee el secreto de firma; lo exige cuando hay base externa o despliegue."""
    secreto = os.environ.get("AUTH_JWT_SECRET", "").strip()
    if secreto:
        return secreto
    if os.environ.get("DATABASE_URL") or os.environ.get("VERCEL"):
        raise RuntimeError(
            "AUTH_JWT_SECRET es obligatorio cuando se usa DATABASE_URL o Vercel"
        )
    return SECRETO_DESARROLLO


def crear_token(usuario: dict[str, Any], secreto: str | None = None) -> str:
    """Firma un token HS256 con el rol y el refugio propietario del usuario."""
    rol = usuario.get("rol")
    if rol not in ROLES:
        raise ValueError(f"rol no soportado: {rol}")
    ahora = datetime.now(timezone.utc)
    carga = {
        "sub": str(usuario["nombre_usuario"]),
        "rol": rol,
        "refugio_id": usuario.get("refugio_id"),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=MINUTOS_TOKEN),
    }
    return jwt.encode(carga, secreto or obtener_secreto_jwt(), algorithm=ALGORITMO)


def decodificar_token(token: str, secreto: str | None = None) -> dict[str, Any]:
    """Verifica firma, expiración y forma del token."""
    try:
        carga = jwt.decode(
            token,
            secreto or obtener_secreto_jwt(),
            algorithms=[ALGORITMO],
            options={"require": ["exp", "sub", "rol"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenInvalido() from exc
    if carga.get("rol") not in ROLES:
        raise TokenInvalido("el token contiene un rol desconocido")
    refugio_id = carga.get("refugio_id")
    if refugio_id is not None and (not isinstance(refugio_id, int) or refugio_id < 1):
        raise TokenInvalido("el token contiene un refugio_id invalido")
    return carga


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(portador),
) -> dict[str, Any]:
    """Dependencia que exige un token Bearer válido."""
    if credenciales is None or credenciales.scheme.lower() != "bearer":
        raise CredencialesInvalidas()
    return decodificar_token(credenciales.credentials)


def requerir_roles(*roles: str) -> Callable[..., dict[str, Any]]:
    """Fábrica de dependencias que restringe el acceso a ciertos roles."""
    permitidos = set(roles)
    if not permitidos <= ROLES:
        raise ValueError(f"roles no soportados: {permitidos - ROLES}")

    def dependencia(
        usuario: dict[str, Any] = Depends(usuario_actual),
    ) -> dict[str, Any]:
        if usuario["rol"] not in permitidos:
            raise RolNoAutorizado(usuario["rol"])
        return usuario

    return dependencia


def verificar_propietario(refugio_id: int, usuario: dict[str, Any]) -> None:
    """RF-05: el refugio solo opera sus fichas; admin puede operar cualquier una."""
    rol = usuario["rol"]
    if rol == "admin":
        return
    if rol != "refugio":
        raise RolNoAutorizado(rol)
    if usuario.get("refugio_id") != refugio_id:
        raise PropietarioNoAutorizado(refugio_id)
