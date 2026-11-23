# -*- coding: utf-8 -*-
"""Crea el esquema aqsis en Supabase y verifica índices y triggers.

Uso:
    python -m persistencia.migrar_supabase

Lee ``DATABASE_URL`` del entorno o de ``.env.local`` (este último no se
versiona). La contraseña de los usuarios demo se hashea en el momento: nunca
se guarda en claro ni se imprime.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from seguridad.autenticacion import hash_contrasena  # noqa: E402

SCHEMA = RAIZ / "persistencia" / "schema_postgres.sql"
SEED = RAIZ / "persistencia" / "seed_postgres.sql"
ENV_LOCAL = RAIZ / ".env.local"
CLAVE_DEMO = "Aqsis2026!"
USUARIOS_DEMO = ("refugio", "adoptante", "admin")
INDICES = {"idx_mascota_catalogo", "idx_mascota_filtros"}
TRIGGERS = {
    "trg_max_fotos",
    "trg_disponible_con_foto",
    "trg_disponible_refugio_verificado",
}


def cargar_env_local() -> None:
    """Carga KEY=VALUE de .env.local sin sobrescribir variables reales."""
    if not ENV_LOCAL.exists():
        return
    for linea in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


def main() -> int:
    cargar_env_local()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit(
            "Falta DATABASE_URL. Definala en el entorno o en proyecto_arq_sis_mascotas/.env.local"
        )

    motor = create_engine(dsn, pool_pre_ping=True)
    with motor.begin() as conexion:
        conexion.exec_driver_sql(SCHEMA.read_text(encoding="utf-8"))
        conexion.exec_driver_sql(SEED.read_text(encoding="utf-8"))

        for nombre in USUARIOS_DEMO:
            conexion.execute(
                text(
                    "UPDATE aqsis.usuario SET contrasena_hash = :hash "
                    "WHERE nombre_usuario = :nombre"
                ),
                {"hash": hash_contrasena(CLAVE_DEMO), "nombre": nombre},
            )

        indices = {
            fila[0]
            for fila in conexion.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE schemaname = 'aqsis'"
                )
            )
        }
        triggers = {
            fila[0]
            for fila in conexion.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE NOT tgisinternal AND tgrelid IN "
                    "('aqsis.mascota'::regclass, 'aqsis.fotografia'::regclass)"
                )
            )
        }
        tablas = {
            fila[0]
            for fila in conexion.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'aqsis'"
                )
            )
        }

    faltan_indices = INDICES - indices
    faltan_triggers = TRIGGERS - triggers
    faltan_tablas = {"refugio", "mascota", "fotografia", "usuario"} - tablas
    if faltan_indices or faltan_triggers or faltan_tablas:
        print("ERROR: falta esquema en PostgreSQL")
        print(f"  tablas: {sorted(faltan_tablas)}")
        print(f"  índices: {sorted(faltan_indices)}")
        print(f"  triggers: {sorted(faltan_triggers)}")
        return 1

    print("PostgreSQL/Supabase listo en el esquema aqsis.")
    print("Tablas: refugio, mascota, fotografia, usuario")
    print("Índices verificados: " + ", ".join(sorted(INDICES)))
    print("Triggers verificados: " + ", ".join(sorted(TRIGGERS)))
    print(f"Usuarios demo actualizados: {', '.join(USUARIOS_DEMO)}")
    print("La contraseña demo se almacenó hasheada; no se muestra.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
