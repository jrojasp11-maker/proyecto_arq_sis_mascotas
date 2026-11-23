# -*- coding: utf-8 -*-
"""Repositorio PostgreSQL del corte vertical (Supabase, esquema aqsis).

Implementa exactamente la misma interfaz que :class:`RepositorioMascotas`, por
lo que los servicios y la API no cambian. Todo el SQL vive en esta capa y usa
el esquema ``aqsis`` de forma explícita.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Mapping, Sequence

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from persistencia.repositorio import (
    CAMPOS_OBLIGATORIOS,
    DatosInvalidos,
    ErrorPersistencia,
    FichaNoEncontrada,
    RefugioNoEncontrado,
    RefugioNoVerificado,
    SinPermiso,
    _es_entero,
    _validar_ficha,
    _validar_fotos,
)


@lru_cache(maxsize=8)
def _motor(dsn: str):
    """Un motor por cadena de conexión: evita abrir un pool por petición."""
    return create_engine(
        dsn,
        # El pooler de Supabase ya valida la sesion. Con ~95 ms de ida y vuelta,
        # un pre-ping por checkout duplicaria la latencia de cada peticion.
        pool_pre_ping=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=10,
        # En modo transaction del pooler, los prepared statements no sobreviven
        # al cierre de transaccion; psycopg los desactiva con prepare_threshold=None.
        connect_args={"prepare_threshold": None},
    )


class RepositorioPostgres:
    """Acceso a datos en PostgreSQL/Supabase con el contrato del repositorio SQLite."""

    def __init__(self, dsn: str):
        if not dsn:
            raise ValueError("DATABASE_URL no puede estar vacia")
        self.dsn = dsn
        self._engine = _motor(dsn)

    # ------------------------------------------------------------------
    # Usuarios de autenticación
    # ------------------------------------------------------------------
    def obtener_usuario(self, nombre_usuario: str) -> dict[str, Any] | None:
        with self._engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conexion:
            fila = conexion.execute(
                text(
                    """
                    SELECT id, nombre_usuario, contrasena_hash, rol, refugio_id, activo
                    FROM aqsis.usuario
                    WHERE nombre_usuario = :nombre AND activo = TRUE
                    """
                ),
                {"nombre": nombre_usuario},
            ).mappings().first()
        if fila is None:
            return None
        usuario = dict(fila)
        usuario["activo"] = bool(usuario["activo"])
        return usuario

    # ------------------------------------------------------------------
    # RF-05: crear / consultar / actualizar / dar de baja una ficha
    # ------------------------------------------------------------------
    def crear_ficha(
        self,
        refugio_id: int,
        ficha: Mapping[str, Any],
        fotografias: Sequence[str] | None = None,
    ) -> int:
        if not _es_entero(refugio_id):
            raise DatosInvalidos("refugio_id debe ser un entero")
        datos = _validar_ficha(ficha)
        fotos = _validar_fotos(fotografias or [])

        try:
            with self._engine.begin() as conexion:
                refugio = conexion.execute(
                    text(
                        "SELECT estado_verificacion FROM aqsis.refugio "
                        "WHERE id = :id FOR UPDATE"
                    ),
                    {"id": refugio_id},
                ).mappings().first()
                if refugio is None:
                    raise RefugioNoEncontrado(refugio_id)
                if refugio["estado_verificacion"] != "verificado":
                    raise RefugioNoVerificado(refugio_id)

                mascota_id = conexion.execute(
                    text(
                        """
                        INSERT INTO aqsis.mascota (
                            refugio_id, nombre, raza, especie, edad_meses, tamano,
                            nivel_energia, experiencia_requerida, apta_con_menores,
                            apta_con_mascotas, historial_salud,
                            historial_comportamiento, estado, fecha_publicacion
                        ) VALUES (
                            :refugio_id, :nombre, :raza, :especie, :edad_meses, :tamano,
                            :nivel_energia, :experiencia_requerida, :apta_con_menores,
                            :apta_con_mascotas, :historial_salud,
                            :historial_comportamiento, 'incompleta', :fecha_publicacion
                        ) RETURNING id
                        """
                    ),
                    {
                        "refugio_id": refugio_id,
                        "nombre": datos["nombre"],
                        "raza": datos.get("raza"),
                        "especie": datos["especie"],
                        "edad_meses": datos["edad_meses"],
                        "tamano": datos["tamano"],
                        "nivel_energia": datos["nivel_energia"],
                        "experiencia_requerida": datos["experiencia_requerida"],
                        "apta_con_menores": datos["apta_con_menores"],
                        "apta_con_mascotas": datos["apta_con_mascotas"],
                        "historial_salud": datos.get("historial_salud"),
                        "historial_comportamiento": datos.get(
                            "historial_comportamiento"
                        ),
                        "fecha_publicacion": datos["fecha_publicacion"],
                    },
                ).scalar_one()

                if fotos:
                    conexion.execute(
                        text(
                            "INSERT INTO aqsis.fotografia (mascota_id, archivo, orden) "
                            "VALUES (:mascota_id, :archivo, :orden)"
                        ),
                        [
                            {"mascota_id": mascota_id, "archivo": archivo, "orden": orden}
                            for archivo, orden in fotos
                        ],
                    )
                    conexion.execute(
                        text(
                            "UPDATE aqsis.mascota SET estado = 'disponible' "
                            "WHERE id = :id"
                        ),
                        {"id": mascota_id},
                    )
                return int(mascota_id)
        except IntegrityError as exc:
            raise ErrorPersistencia("ERR-006", str(exc)) from exc

    def obtener_por_id(self, mascota_id: int) -> dict[str, Any] | None:
        if not _es_entero(mascota_id):
            raise DatosInvalidos("mascota_id debe ser un entero")

        with self._engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conexion:
            fila = conexion.execute(
                text(
                    """
                    SELECT m.id, m.refugio_id, m.nombre, m.raza, m.especie,
                           m.edad_meses, m.tamano, m.nivel_energia,
                           m.experiencia_requerida, m.apta_con_menores,
                           m.apta_con_mascotas, m.historial_salud,
                           m.historial_comportamiento, m.estado,
                           m.fecha_publicacion, m.creado_en::text AS creado_en,
                           r.nombre AS refugio_nombre,
                           r.localidad AS refugio_localidad,
                           r.estado_verificacion AS refugio_estado
                    FROM aqsis.mascota m
                    JOIN aqsis.refugio r ON r.id = m.refugio_id
                    WHERE m.id = :id
                    """
                ),
                {"id": mascota_id},
            ).mappings().first()
            if fila is None:
                return None
            fotos = conexion.execute(
                text(
                    "SELECT id, archivo, orden FROM aqsis.fotografia "
                    "WHERE mascota_id = :id ORDER BY orden"
                ),
                {"id": mascota_id},
            ).mappings().all()

        resultado = dict(fila)
        resultado["apta_con_menores"] = bool(resultado["apta_con_menores"])
        resultado["apta_con_mascotas"] = bool(resultado["apta_con_mascotas"])
        resultado["fotografias"] = [dict(foto) for foto in fotos]
        return resultado

    def actualizar_ficha(
        self,
        mascota_id: int,
        refugio_id: int,
        cambios: Mapping[str, Any],
        fotografias: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        if not cambios and fotografias is None:
            raise DatosInvalidos("no hay cambios para aplicar")

        try:
            with self._engine.begin() as conexion:
                actual = conexion.execute(
                    text(
                        "SELECT * FROM aqsis.mascota WHERE id = :id FOR UPDATE"
                    ),
                    {"id": mascota_id},
                ).mappings().first()
                if actual is None:
                    raise FichaNoEncontrada(mascota_id)
                if actual["refugio_id"] != refugio_id:
                    raise SinPermiso(mascota_id)

                campos_permitidos = set(CAMPOS_OBLIGATORIOS) | {
                    "raza",
                    "historial_salud",
                    "historial_comportamiento",
                }
                desconocidos = set(cambios) - campos_permitidos
                if desconocidos:
                    raise DatosInvalidos(
                        f"campos no permitidos: {', '.join(sorted(desconocidos))}"
                    )

                combinada = {clave: actual[clave] for clave in CAMPOS_OBLIGATORIOS}
                combinada.update(
                    {
                        clave: actual[clave]
                        for clave in (
                            "raza",
                            "historial_salud",
                            "historial_comportamiento",
                        )
                    }
                )
                combinada.update(cambios)
                datos = _validar_ficha(combinada)

                conexion.execute(
                    text(
                        """
                        UPDATE aqsis.mascota SET
                            nombre = :nombre, raza = :raza, especie = :especie,
                            edad_meses = :edad_meses, tamano = :tamano,
                            nivel_energia = :nivel_energia,
                            experiencia_requerida = :experiencia_requerida,
                            apta_con_menores = :apta_con_menores,
                            apta_con_mascotas = :apta_con_mascotas,
                            historial_salud = :historial_salud,
                            historial_comportamiento = :historial_comportamiento,
                            fecha_publicacion = :fecha_publicacion
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": mascota_id,
                        "nombre": datos["nombre"],
                        "raza": datos.get("raza"),
                        "especie": datos["especie"],
                        "edad_meses": datos["edad_meses"],
                        "tamano": datos["tamano"],
                        "nivel_energia": datos["nivel_energia"],
                        "experiencia_requerida": datos["experiencia_requerida"],
                        "apta_con_menores": datos["apta_con_menores"],
                        "apta_con_mascotas": datos["apta_con_mascotas"],
                        "historial_salud": datos.get("historial_salud"),
                        "historial_comportamiento": datos.get(
                            "historial_comportamiento"
                        ),
                        "fecha_publicacion": datos["fecha_publicacion"],
                    },
                )

                if fotografias is not None:
                    fotos = _validar_fotos(fotografias)
                    conexion.execute(
                        text(
                            "DELETE FROM aqsis.fotografia WHERE mascota_id = :id"
                        ),
                        {"id": mascota_id},
                    )
                    if fotos:
                        conexion.execute(
                            text(
                                "INSERT INTO aqsis.fotografia "
                                "(mascota_id, archivo, orden) "
                                "VALUES (:mascota_id, :archivo, :orden)"
                            ),
                            [
                                {
                                    "mascota_id": mascota_id,
                                    "archivo": archivo,
                                    "orden": orden,
                                }
                                for archivo, orden in fotos
                            ],
                        )
                    conexion.execute(
                        text(
                            "UPDATE aqsis.mascota SET estado = :estado WHERE id = :id"
                        ),
                        {
                            "id": mascota_id,
                            "estado": "disponible" if fotos else "incompleta",
                        },
                    )
        except IntegrityError as exc:
            raise ErrorPersistencia("ERR-006", str(exc)) from exc

        ficha = self.obtener_por_id(mascota_id)
        assert ficha is not None
        return ficha

    def dar_de_baja(self, mascota_id: int, refugio_id: int) -> None:
        with self._engine.begin() as conexion:
            actual = conexion.execute(
                text(
                    "SELECT refugio_id FROM aqsis.mascota WHERE id = :id FOR UPDATE"
                ),
                {"id": mascota_id},
            ).mappings().first()
            if actual is None:
                raise FichaNoEncontrada(mascota_id)
            if actual["refugio_id"] != refugio_id:
                raise SinPermiso(mascota_id)
            conexion.execute(
                text("UPDATE aqsis.mascota SET estado = 'baja' WHERE id = :id"),
                {"id": mascota_id},
            )

    # ------------------------------------------------------------------
    # RF-34: catálogo de mascotas disponibles
    # ------------------------------------------------------------------
    def listar_catalogo(
        self,
        especie: str | None = None,
        tamano: str | None = None,
        edad_min: int | None = None,
        edad_max: int | None = None,
        pagina: int = 1,
        por_pagina: int = 20,
    ) -> dict[str, Any]:
        # Mismas validaciones que el repositorio SQLite: el contrato no cambia.
        if especie is not None and especie not in {"perro", "gato"}:
            raise DatosInvalidos("especie debe ser perro o gato")
        if tamano is not None and tamano not in {"pequeno", "mediano", "grande"}:
            raise DatosInvalidos("tamano debe ser pequeno, mediano o grande")
        if edad_min is not None and (not _es_entero(edad_min) or edad_min < 0):
            raise DatosInvalidos("edad_min debe ser un entero mayor o igual a 0")
        if edad_max is not None and (not _es_entero(edad_max) or edad_max < 0):
            raise DatosInvalidos("edad_max debe ser un entero mayor o igual a 0")
        if edad_min is not None and edad_max is not None and edad_min > edad_max:
            raise DatosInvalidos("edad_min no puede ser mayor que edad_max")
        if not _es_entero(pagina) or pagina < 1:
            raise DatosInvalidos("pagina debe ser un entero mayor o igual a 1")
        if not _es_entero(por_pagina) or not (1 <= por_pagina <= 100):
            raise DatosInvalidos("por_pagina debe estar entre 1 y 100")

        condiciones = [
            "m.estado = 'disponible'",
            "r.estado_verificacion = 'verificado'",
        ]
        parametros: dict[str, Any] = {}
        if especie is not None:
            condiciones.append("m.especie = :especie")
            parametros["especie"] = especie
        if tamano is not None:
            condiciones.append("m.tamano = :tamano")
            parametros["tamano"] = tamano
        if edad_min is not None:
            condiciones.append("m.edad_meses >= :edad_min")
            parametros["edad_min"] = edad_min
        if edad_max is not None:
            condiciones.append("m.edad_meses <= :edad_max")
            parametros["edad_max"] = edad_max

        where = " AND ".join(condiciones)
        parametros["limite"] = por_pagina
        parametros["desplazamiento"] = (pagina - 1) * por_pagina

        # Una sola ida a la base: COUNT(*) OVER() devuelve el total junto con
        # la pagina. Así se conserva el contrato con la mitad de latencia.
        consulta = f"""
            WITH filtradas AS (
                SELECT m.id, m.nombre, m.especie, m.edad_meses, m.tamano,
                       m.nivel_energia, m.fecha_publicacion,
                       r.id AS refugio_id, r.nombre AS refugio_nombre,
                       r.localidad AS refugio_localidad,
                       (SELECT f.archivo FROM aqsis.fotografia f
                         WHERE f.mascota_id = m.id
                         ORDER BY f.orden LIMIT 1) AS foto_principal,
                       COUNT(*) OVER() AS total_total
                FROM aqsis.mascota m
                JOIN aqsis.refugio r ON r.id = m.refugio_id
                WHERE {where}
            )
            SELECT * FROM filtradas
            ORDER BY fecha_publicacion ASC, id ASC
            LIMIT :limite OFFSET :desplazamiento
        """
        with self._engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conexion:
            filas = conexion.execute(
                text(consulta), parametros
            ).mappings().all()
            if filas:
                total = filas[0]["total_total"]
            else:
                # La pagina puede estar fuera de rango; el total sigue siendo util.
                total = conexion.execute(
                    text(
                        f"""
                        SELECT COUNT(*)
                        FROM aqsis.mascota m
                        JOIN aqsis.refugio r ON r.id = m.refugio_id
                        WHERE {where}
                        """
                    ),
                    parametros,
                ).scalar_one()

        mascotas = []
        for fila in filas:
            item = dict(fila)
            item.pop("total_total", None)
            mascotas.append(item)
        return {
            "total": int(total),
            "pagina": pagina,
            "porPagina": por_pagina,
            "mascotas": mascotas,
        }

    def contar_fichas(self) -> int:
        with self._engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conexion:
            return int(
                conexion.execute(
                    text("SELECT COUNT(*) FROM aqsis.mascota")
                ).scalar_one()
            )
