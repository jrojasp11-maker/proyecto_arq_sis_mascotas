# -*- coding: utf-8 -*-
"""API REST del corte vertical (semana 14).

Flujo: HTTP -> servicio de aplicación -> repositorio -> SQLite.
La API solo recibe y valida la forma de la petición; las reglas del negocio
viven en el repositorio/servicio y el SQL no sale de ``persistencia``.
"""

from __future__ import annotations

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.dependencias import obtener_servicio_catalogo, obtener_servicio_mascotas
from api.esquemas import (
    MascotaActualizar,
    MascotaCrear,
    MascotaRespuesta,
    PaginaCatalogo,
)
from persistencia.repositorio import ErrorPersistencia
from servicios.servicio_catalogo import ServicioCatalogo
from servicios.servicio_mascotas import ServicioMascotas

logger = logging.getLogger("aqsis.api")

# Traducción del catálogo de errores del dominio a códigos HTTP.
CODIGOS_HTTP = {
    "ERR-003": 403,  # la ficha no pertenece al refugio
    "ERR-004": 400,  # datos inválidos
    "ERR-006": 409,  # violación de integridad
    "ERR-008": 404,  # refugio inexistente
    "ERR-009": 409,  # refugio no verificado
    "ERR-011": 404,  # ficha inexistente
}

ORIGENES_CORS = [
    origen.strip()
    for origen in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
    ).split(",")
    if origen.strip()
]

app = FastAPI(
    title="Adopción responsable de mascotas API",
    version="1.0.0",
    description=(
        "Corte vertical de la semana 14: RF-05 (gestión de la ficha de mascota) "
        "y RF-34 (consulta del catálogo)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_CORS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ErrorPersistencia)
async def manejar_error_persistencia(
    request: Request, exc: ErrorPersistencia
) -> JSONResponse:
    estado = CODIGOS_HTTP.get(exc.codigo, 500)
    return JSONResponse(
        status_code=estado,
        content={"detail": exc.mensaje, "codigo": exc.codigo},
    )


@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    partes: list[str] = []
    for error in exc.errors():
        ubicacion = ".".join(
            str(paso)
            for paso in error.get("loc", ())
            if paso not in ("body", "query", "path")
        )
        mensaje = str(error.get("msg", "dato inválido"))
        partes.append(f"{ubicacion}: {mensaje}" if ubicacion else mensaje)
    detalle = "datos de entrada inválidos"
    if partes:
        detalle = f"{detalle}: {'; '.join(partes)}"
    return JSONResponse(
        status_code=400,
        content={"detail": detalle, "codigo": "ERR-004"},
    )


@app.exception_handler(Exception)
async def manejar_error_inesperado(
    request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(
        "Error no controlado en %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor.", "codigo": "ERR-500"},
    )


router = APIRouter(prefix="/api/v1", tags=["mascotas"])


@router.post(
    "/mascotas",
    response_model=MascotaRespuesta,
    status_code=201,
    summary="RF-05: registrar una ficha de mascota",
    responses={
        400: {"description": "Datos inválidos (ERR-004)"},
        404: {"description": "Refugio inexistente (ERR-008)"},
        409: {"description": "Refugio no verificado (ERR-009)"},
    },
)
def crear_mascota(
    datos: MascotaCrear,
    servicio: ServicioMascotas = Depends(obtener_servicio_mascotas),
) -> dict:
    return servicio.crear(datos.model_dump())


@router.put(
    "/mascotas/{mascota_id}",
    response_model=MascotaRespuesta,
    summary="RF-05: actualizar una ficha de mascota",
    responses={
        400: {"description": "Datos inválidos (ERR-004)"},
        403: {"description": "La ficha no pertenece al refugio (ERR-003)"},
        404: {"description": "Ficha inexistente (ERR-011)"},
    },
)
def actualizar_mascota(
    mascota_id: Annotated[int, Path(gt=0)],
    datos: MascotaActualizar,
    servicio: ServicioMascotas = Depends(obtener_servicio_mascotas),
) -> dict:
    return servicio.actualizar(mascota_id, datos.model_dump(exclude_unset=True))


@router.delete(
    "/mascotas/{mascota_id}",
    status_code=204,
    summary="RF-05: dar de baja una ficha de mascota",
    responses={
        403: {"description": "La ficha no pertenece al refugio (ERR-003)"},
        404: {"description": "Ficha inexistente (ERR-011)"},
    },
)
def dar_de_baja_mascota(
    mascota_id: Annotated[int, Path(gt=0)],
    refugio_id: Annotated[int, Query(gt=0, description="Refugio dueño de la ficha")],
    servicio: ServicioMascotas = Depends(obtener_servicio_mascotas),
) -> Response:
    servicio.dar_de_baja(mascota_id, refugio_id)
    return Response(status_code=204)


@router.get(
    "/mascotas",
    response_model=PaginaCatalogo,
    summary="RF-34: consultar el catálogo de mascotas disponibles",
    responses={400: {"description": "Filtro o paginación inválidos (ERR-004)"}},
)
def listar_catalogo(
    especie: Annotated[str | None, Query(description="perro o gato")] = None,
    tamano: Annotated[
        str | None, Query(description="pequeno, mediano o grande")
    ] = None,
    edad_min: Annotated[int | None, Query(ge=0)] = None,
    edad_max: Annotated[int | None, Query(ge=0)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=100)] = 20,
    servicio: ServicioCatalogo = Depends(obtener_servicio_catalogo),
) -> dict:
    return servicio.listar(
        especie=especie,
        tamano=tamano,
        edad_min=edad_min,
        edad_max=edad_max,
        pagina=pagina,
        por_pagina=por_pagina,
    )


app.include_router(router)


@app.get("/", include_in_schema=False)
def raiz() -> dict:
    return {
        "servicio": "API de adopción responsable de mascotas",
        "version": "1.0.0",
        "documentacion": "/docs",
        "openapi": "/openapi.json",
    }
