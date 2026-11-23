# -*- coding: utf-8 -*-
"""Verificación HTTP real de la API contra PostgreSQL/Supabase.

Genera ``evidencias/supabase_verificacion.txt``. No imprime ni guarda la
DATABASE_URL ni los tokens. Comprueba autenticación por rol, RF-05, RF-34,
persistencia en el esquema ``aqsis`` y uso posible de los índices con EXPLAIN.

Uso:
    python -m pruebas.verificar_supabase
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from persistencia.migrar_supabase import cargar_env_local
from pruebas.servidor import servidor_api

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "evidencias" / "supabase_verificacion.txt"
CLAVE_DEMO = "Aqsis2026!"
BASE = "/api/v1"


def login(cliente: httpx.Client, usuario: str) -> str:
    respuesta = cliente.post(
        BASE + "/auth/token",
        json={"usuario": usuario, "contrasena": CLAVE_DEMO},
    )
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()["access_token"]


def main() -> int:
    cargar_env_local()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise SystemExit("Falta DATABASE_URL en .env.local")

    motor = create_engine(dsn, pool_pre_ping=True)
    lineas: list[str] = [
        "VERIFICACION DE POSTGRESQL/SUPABASE - CORTE VERTICAL",
        "=" * 78,
        f"Fecha de ejecucion: {dt.datetime.now().isoformat(timespec='seconds')}",
        "Base: PostgreSQL en Supabase | Esquema: aqsis | Motor: SQLAlchemy 2.x",
        "Cliente: httpx real | Servidor: Uvicorn temporal",
        "=" * 78,
        "",
    ]
    errores: list[str] = []

    def chequear(condicion: bool, texto: str) -> None:
        if not condicion:
            errores.append(texto)

    with motor.connect() as conexion:
        inicial = conexion.execute(
            text("SELECT COUNT(*) FROM aqsis.mascota")
        ).scalar_one()
        esquema = conexion.execute(text("SELECT current_schema()")).scalar_one()
    lineas.append(f"SQL directo | current_schema={esquema}; mascotas={inicial}")
    chequear(inicial >= 6, "la carga inicial de aqsis no esta presente")

    with servidor_api(usar_postgres=True) as url_base:
        with httpx.Client(base_url=url_base, timeout=30) as anonimo:
            sin_token = anonimo.post(
                BASE + "/mascotas",
                json={
                    "refugio_id": 1,
                    "nombre": "SinToken",
                    "especie": "perro",
                    "edad_meses": 12,
                    "tamano": "mediano",
                    "nivel_energia": "media",
                    "experiencia_requerida": "basica",
                    "apta_con_menores": True,
                    "apta_con_mascotas": True,
                    "fecha_publicacion": "2026-11-20",
                    "fotografias": ["sin_token.jpg"],
                },
            )
            lineas.append(
                f"AUTH | POST sin token -> HTTP {sin_token.status_code}; "
                f"codigo {sin_token.json().get('codigo')}"
            )
            chequear(sin_token.status_code == 401, "la API no exige token")

        with httpx.Client(base_url=url_base, timeout=30) as adoptante:
            adoptante.headers.update(
                {"Authorization": f"Bearer {login(adoptante, 'adoptante')}"}
            )
            catalogo = adoptante.get(BASE + "/mascotas")
            lineas.append(
                f"AUTH | rol adoptante, GET catalogo -> HTTP {catalogo.status_code}; "
                f"total {catalogo.json().get('total')}"
            )
            chequear(catalogo.status_code == 200, "el adoptante no puede consultar el catalogo")
            rechazo = adoptante.post(
                BASE + "/mascotas",
                json={
                    "refugio_id": 1,
                    "nombre": "AdoptanteEscribe",
                    "especie": "perro",
                    "edad_meses": 12,
                    "tamano": "mediano",
                    "nivel_energia": "media",
                    "experiencia_requerida": "basica",
                    "apta_con_menores": True,
                    "apta_con_mascotas": True,
                    "fecha_publicacion": "2026-11-20",
                    "fotografias": ["adoptante.jpg"],
                },
            )
            lineas.append(
                f"AUTH | rol adoptante, POST -> HTTP {rechazo.status_code}; "
                f"codigo {rechazo.json().get('codigo')}"
            )
            chequear(rechazo.status_code == 403, "el adoptante puede escribir fichas")

        with httpx.Client(base_url=url_base, timeout=30) as refugio:
            refugio.headers.update(
                {"Authorization": f"Bearer {login(refugio, 'refugio')}"}
            )
            cuerpo = {
                "refugio_id": 1,
                "nombre": "PersistenciaSupabase",
                "raza": "Mestiza",
                "especie": "perro",
                "edad_meses": 18,
                "tamano": "mediano",
                "nivel_energia": "media",
                "experiencia_requerida": "basica",
                "apta_con_menores": True,
                "apta_con_mascotas": True,
                "historial_salud": "Vacunas al dia",
                "historial_comportamiento": "Sociable",
                "fecha_publicacion": "2026-11-20",
                "fotografias": ["supabase_01.jpg", "supabase_02.jpg"],
            }
            crear = refugio.post(BASE + "/mascotas", json=cuerpo)
            lineas.append(
                f"RF-05 | POST con rol refugio -> HTTP {crear.status_code}; "
                f"estado {crear.json().get('estado')}"
            )
            chequear(crear.status_code == 201, "POST contra PostgreSQL fallo")
            nuevo_id = crear.json().get("id") if crear.status_code == 201 else None

            ajeno = refugio.post(BASE + "/mascotas", json={**cuerpo, "refugio_id": 2})
            lineas.append(
                f"RF-05 | refugio 1 intenta publicar por refugio 2 -> HTTP {ajeno.status_code}; "
                f"codigo {ajeno.json().get('codigo')}"
            )
            chequear(ajeno.status_code == 403, "no se verifico la autorizacion por propietario")

            if nuevo_id is not None:
                edicion = refugio.put(
                    f"{BASE}/mascotas/{nuevo_id}",
                    json={"refugio_id": 1, "nombre": "PersistenciaSupabaseEditada"},
                )
                lineas.append(
                    f"RF-05 | PUT /mascotas/{nuevo_id} -> HTTP {edicion.status_code}; "
                    f"nombre {edicion.json().get('nombre')}"
                )
                chequear(edicion.status_code == 200, "PUT contra PostgreSQL fallo")
                chequear(
                    edicion.json().get("nombre") == "PersistenciaSupabaseEditada",
                    "la edicion no se persistio en PostgreSQL",
                )

                catalogo_despues = refugio.get(BASE + "/mascotas")
                ids = [m["id"] for m in catalogo_despues.json().get("mascotas", [])]
                lineas.append(
                    f"RF-34 | GET catalogo tras crear -> HTTP {catalogo_despues.status_code}; "
                    f"total {catalogo_despues.json().get('total')}; id {nuevo_id} presente: {nuevo_id in ids}"
                )
                chequear(nuevo_id in ids, "la ficha creada no aparecio en el catalogo")

        with httpx.Client(base_url=url_base, timeout=30) as admin:
            admin.headers.update(
                {"Authorization": f"Bearer {login(admin, 'admin')}"}
            )
            cuerpo_admin = {
                "refugio_id": 2,
                "nombre": "AdminPruebaRN03",
                "especie": "perro",
                "edad_meses": 12,
                "tamano": "mediano",
                "nivel_energia": "media",
                "experiencia_requerida": "basica",
                "apta_con_menores": True,
                "apta_con_mascotas": True,
                "fecha_publicacion": "2026-11-20",
                "fotografias": ["admin.jpg"],
            }
            respuesta_admin = admin.post(BASE + "/mascotas", json=cuerpo_admin)
            lineas.append(
                f"AUTH | admin publica por refugio 2 -> HTTP {respuesta_admin.status_code}; "
                f"codigo {respuesta_admin.json().get('codigo')} (RN-03)"
            )
            chequear(respuesta_admin.status_code == 409, "admin no llego a la regla RN-03")

            if nuevo_id is not None:
                baja = admin.delete(
                    f"{BASE}/mascotas/{nuevo_id}", params={"refugio_id": 1}
                )
                lineas.append(
                    f"RF-05 | admin da de baja la ficha {nuevo_id} -> HTTP {baja.status_code}"
                )
                chequear(baja.status_code == 204, "DELETE contra PostgreSQL fallo")

        if nuevo_id is not None:
            with httpx.Client(base_url=url_base, timeout=30) as verificador:
                verificador.headers.update(
                    {"Authorization": f"Bearer {login(verificador, 'refugio')}"}
                )
                final = verificador.get(BASE + "/mascotas")
                ids_final = [m["id"] for m in final.json().get("mascotas", [])]
                lineas.append(
                    f"RF-34 | catalogo tras baja: id {nuevo_id} ausente: {nuevo_id not in ids_final}"
                )
                chequear(nuevo_id not in ids_final, "la baja no se reflejo en el catalogo")

    with motor.connect() as conexion:
        if nuevo_id is not None:
            estado_bd = conexion.execute(
                text("SELECT estado FROM aqsis.mascota WHERE id = :id"),
                {"id": nuevo_id},
            ).scalar_one()
            lineas.append(f"SQL directo | ficha {nuevo_id} estado final={estado_bd}")
            chequear(estado_bd == "baja", "la baja no se persistio en PostgreSQL")

        conexion.execute(text("SET enable_seqscan = off"))
        plan = "\n".join(
            fila[0]
            for fila in conexion.execute(
                text(
                    """
                    EXPLAIN
                    SELECT m.id, m.nombre, m.fecha_publicacion,
                           r.nombre AS refugio_nombre
                    FROM aqsis.mascota m
                    JOIN aqsis.refugio r ON r.id = m.refugio_id
                    WHERE m.estado = 'disponible'
                      AND r.estado_verificacion = 'verificado'
                    ORDER BY m.fecha_publicacion ASC, m.id ASC
                    LIMIT 20
                    """
                )
            )
        )
        lineas.extend(
            [
                "",
                "INDICES | EXPLAIN del catálogo (enable_seqscan=off para forzar la comparación):",
                plan,
            ]
        )
        chequear(
            "idx_mascota_catalogo" in plan,
            "EXPLAIN no mostro el indice idx_mascota_catalogo",
        )

    lineas.extend(["", "=" * 78])
    if errores:
        lineas.append("RESULTADO: NO CUMPLE")
        lineas.extend(f"  - {error}" for error in errores)
        codigo = 1
    else:
        lineas.append("RESULTADO: CUMPLE. PostgreSQL, roles y contratos verificados.")
        codigo = 0
    lineas.append("=" * 78)

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas[-18:]))
    print(f"\nEvidencia escrita en: {SALIDA}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
