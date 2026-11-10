# -*- coding: utf-8 -*-
"""Servicio de aplicación del RF-05: gestión de la ficha de mascota.

El servicio coordina el caso de uso, aplica las reglas de negocio a través del
repositorio y traduce la ausencia de una ficha a una excepción de dominio.
No construye SQL ni conoce detalles de HTTP.
"""

from __future__ import annotations

from typing import Any, Mapping

from persistencia.repositorio import FichaNoEncontrada, RepositorioMascotas


class ServicioMascotas:
    """Caso de uso RF-05: crear, consultar, editar y dar de baja una ficha."""

    def __init__(self, repositorio: RepositorioMascotas):
        self.repositorio = repositorio

    def crear(self, datos: Mapping[str, Any]) -> dict[str, Any]:
        """Registra una ficha y devuelve la ficha completa con su id real."""
        datos = dict(datos)
        refugio_id = datos.pop("refugio_id")
        fotografias = datos.pop("fotografias", [])
        mascota_id = self.repositorio.crear_ficha(refugio_id, datos, fotografias)
        return self.consultar(mascota_id)

    def consultar(self, mascota_id: int) -> dict[str, Any]:
        """Recupera una ficha o lanza ``FichaNoEncontrada`` (ERR-011)."""
        ficha = self.repositorio.obtener_por_id(mascota_id)
        if ficha is None:
            raise FichaNoEncontrada(mascota_id)
        return ficha

    def actualizar(
        self, mascota_id: int, datos: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Actualiza los campos enviados y, si vienen, reemplaza las fotos."""
        datos = dict(datos)
        refugio_id = datos.pop("refugio_id")
        fotografias = datos.pop("fotografias", None)
        return self.repositorio.actualizar_ficha(
            mascota_id, refugio_id, datos, fotografias
        )

    def dar_de_baja(self, mascota_id: int, refugio_id: int) -> None:
        """Baja lógica: la ficha deja de aparecer en el catálogo (RN-15)."""
        self.repositorio.dar_de_baja(mascota_id, refugio_id)
