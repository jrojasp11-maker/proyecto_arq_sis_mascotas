# -*- coding: utf-8 -*-
"""Servicio de aplicación del RF-34: consulta del catálogo de mascotas.

El servicio delega los filtros y la paginación en el repositorio y normaliza
la respuesta al contrato JSON de la API (nombres en snake_case).
"""

from __future__ import annotations

from typing import Any

from persistencia.repositorio import RepositorioMascotas


class ServicioCatalogo:
    """Caso de uso RF-34: listar y filtrar las fichas publicadas."""

    def __init__(self, repositorio: RepositorioMascotas):
        self.repositorio = repositorio

    def listar(
        self,
        especie: str | None = None,
        tamano: str | None = None,
        edad_min: int | None = None,
        edad_max: int | None = None,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> dict[str, Any]:
        resultado = self.repositorio.listar_catalogo(
            especie=especie,
            tamano=tamano,
            edad_min=edad_min,
            edad_max=edad_max,
            pagina=pagina,
            por_pagina=por_pagina,
        )
        return {
            "total": resultado["total"],
            "pagina": resultado["pagina"],
            "por_pagina": resultado["porPagina"],
            "mascotas": resultado["mascotas"],
        }
