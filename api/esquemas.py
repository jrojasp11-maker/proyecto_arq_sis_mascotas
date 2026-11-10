# -*- coding: utf-8 -*-
"""Contratos JSON de entrada y salida de la API (Pydantic v2)."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class FotografiaRespuesta(BaseModel):
    id: int
    archivo: str
    orden: int


class MascotaRespuesta(BaseModel):
    """Ficha completa devuelta por POST y PUT (RF-05)."""

    id: int
    refugio_id: int
    nombre: str
    raza: str | None = None
    especie: str
    edad_meses: int
    tamano: str
    nivel_energia: str
    experiencia_requerida: str
    apta_con_menores: bool
    apta_con_mascotas: bool
    historial_salud: str | None = None
    historial_comportamiento: str | None = None
    estado: str
    fecha_publicacion: date
    creado_en: str | None = None
    refugio_nombre: str
    refugio_localidad: str
    refugio_estado: str
    fotografias: list[FotografiaRespuesta] = Field(default_factory=list)


class MascotaCrear(BaseModel):
    """Cuerpo de POST /mascotas. ``refugio_id`` representa al actor mientras
    la autenticación queda para la semana 3."""

    refugio_id: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=60)
    raza: str | None = Field(default=None, max_length=80)
    especie: str
    edad_meses: int = Field(ge=0, le=300)
    tamano: str
    nivel_energia: str
    experiencia_requerida: str
    apta_con_menores: bool
    apta_con_mascotas: bool
    historial_salud: str | None = Field(default=None, max_length=1000)
    historial_comportamiento: str | None = Field(default=None, max_length=1000)
    fecha_publicacion: date
    fotografias: list[str] = Field(default_factory=list)


class MascotaActualizar(BaseModel):
    """Cuerpo de PUT /mascotas/{id}: todos los campos son opcionales."""

    refugio_id: int = Field(gt=0)
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    raza: str | None = Field(default=None, max_length=80)
    especie: str | None = None
    edad_meses: int | None = Field(default=None, ge=0, le=300)
    tamano: str | None = None
    nivel_energia: str | None = None
    experiencia_requerida: str | None = None
    apta_con_menores: bool | None = None
    apta_con_mascotas: bool | None = None
    historial_salud: str | None = Field(default=None, max_length=1000)
    historial_comportamiento: str | None = Field(default=None, max_length=1000)
    fecha_publicacion: date | None = None
    fotografias: list[str] | None = None


class MascotaCatalogo(BaseModel):
    """Fila del catálogo (RF-34). No incluye datos personales (RNF-04)."""

    id: int
    nombre: str
    especie: str
    edad_meses: int
    tamano: str
    nivel_energia: str
    fecha_publicacion: date
    refugio_id: int
    refugio_nombre: str
    refugio_localidad: str
    foto_principal: str | None = None


class PaginaCatalogo(BaseModel):
    total: int
    pagina: int
    por_pagina: int
    mascotas: list[MascotaCatalogo]
