# Corte vertical semanas 13–14 — Persistencia, servicios y API de RF-05 y RF-34

Repositorio: <https://github.com/jrojasp11-maker/proyecto_arq_sis_mascotas>

Proyecto: **Sistema de Apoyo a la Decisión para la Adopción Responsable de Mascotas mediante Inteligencia Artificial**.

## Contexto y alcance

Este repositorio documenta el corte vertical de **Arquitectura de Sistemas I**
sobre el caso de estudio de **Práctica de Ingeniería**: los refugios publican
fichas de mascotas y los adoptantes consultan el catálogo. En esta entrega no se
implementa la inteligencia artificial.

| Semana | Trabajo | Evidencia |
|---|---|---|
| 13 | Persistencia de los dos RF priorizados | Esquema, repositorio y 12 pruebas |
| **14** | **Servicios, API, contratos y verificación de RNF** | **API FastAPI, 39 pruebas y evidencias de calidad** |
| 3 (prototipo) | Interfaz y cierre | Pendiente: pantalla, autenticación y carga |

| Orden | RF | Resultado observable |
|---|---|---|
| 1 | **RF-05 — Gestión de la ficha de mascota** | El refugio crea, actualiza o da de baja una ficha; obtiene su `id` y su estado (`incompleta` o `disponible`). |
| 2 | **RF-34 — Consulta del catálogo** | El adoptante lista fichas disponibles con filtros por especie, tamaño y edad, con paginación y orden estable. |

**Stack:** Python 3.12 + FastAPI + Pydantic v2 + SQLite 3. La base objetivo del
proyecto sigue siendo PostgreSQL (ADR-03/ADR-10); SQLite se usa para reproducir
el corte sin instalar un servidor. El SQL está encapsulado en
`persistencia/repositorio.py` y no se repite en la API.

## 1. Requisitos e instalación

- **Python 3.12.10** (probado con esta versión; funciona con 3.10 o superior).
- **SQLite 3.49.1** (incluido en Python; no requiere servidor).
- Dependencias de la API y las pruebas: `requirements.txt`.

Desde PowerShell, en la raíz del repositorio:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

> Si la activación de PowerShell está restringida, use directamente
> `.\.venv\Scripts\python.exe` en lugar de `python` en los comandos siguientes.

## 2. Estructura

```text
proyecto_arq_sis_mascotas/
├── api/
│   ├── main.py                 # rutas, CORS y traducción de errores a HTTP
│   ├── esquemas.py             # contratos Pydantic de entrada y salida
│   └── dependencias.py         # inyección del repositorio y los servicios
├── servicios/
│   ├── servicio_mascotas.py    # RF-05: crear, consultar, actualizar, baja
│   └── servicio_catalogo.py    # RF-34: listar y filtrar el catálogo
├── persistencia/
│   ├── schema.sql              # tablas, índices, CHECK, FK y triggers
│   ├── seed.sql                # estado inicial conocido
│   ├── repositorio.py          # RepositorioMascotas (todo el SQL)
│   ├── inicializar_db.py       # crea/reinicia la base de la API
│   ├── prueba_persistencia.py  # 12 pruebas de la semana 13
│   └── demo_consulta.py        # consulta manual del catálogo
├── pruebas/
│   ├── test_rf05_api.py        # pruebas funcionales de RF-05
│   ├── test_rf34_api.py        # pruebas funcionales de RF-34
│   ├── test_rnf10_integridad.py# matriz de entradas inválidas
│   ├── test_servicios_aislados.py # RNF-08 con doble de repositorio
│   ├── rnf_desempeno.py        # RNF-05: 20 consultas por HTTP real
│   ├── demo_api.py             # demostración HTTP de ambos RF
│   └── servidor.py             # Uvicorn temporal para las verificaciones
├── docs/
│   ├── contratos_api.md        # contratos completos de los endpoints
│   └── informe_semanas_13_14.md # informe combinado de las semanas 13 y 14
├── evidencias/
│   ├── salida_pruebas.txt      # 12 pruebas de persistencia (semana 13)
│   ├── salida_pruebas_semana14.txt # 39 pruebas de la semana 14
│   ├── cobertura.txt           # cobertura de servicios (RNF-08)
│   ├── rnf_desempeno.txt       # resultados de RNF-05
│   ├── demo_api.txt            # peticiones y respuestas HTTP reales
│   ├── prueba.db               # base de la semana 13
│   └── api.db / demo_api.db / rnf_desempeno.db # bases locales (no versionadas)
└── plantilla/
    ├── plantilla_13_1.tex      # documento formal de la semana 13
    └── plantilla_13_1.pdf      # versión compilada
```

## 3. Arquitectura y responsabilidades

Flujo del backend:

```text
HTTP -> API -> Servicio de aplicación -> Repositorio -> Base de datos
```

| Capa | Dónde | Responsabilidad |
|---|---|---|
| API | `api/main.py` | Recibir HTTP, validar la forma, delegar y traducir errores a códigos HTTP. No contiene reglas ni SQL. |
| Servicio | `servicios/` | Coordinar el caso de uso, normalizar la respuesta y decidir la ausencia de una ficha. |
| Repositorio | `persistencia/repositorio.py` | Todo el SQL, las validaciones de dominio y las transacciones. |
| Base de datos | SQLite | `refugio`, `mascota`, `fotografia`, con CHECK, FK, índices y triggers. |

Esto permite probar los servicios con un doble del repositorio (RNF-08) sin abrir
una base real, y mantener el SQL fuera de la API.

## 4. Ejecutar la API

```powershell
# 1) Crear o reiniciar la base con el estado inicial conocido
python -m persistencia.inicializar_db

# 2) Levantar la API
uvicorn api.main:app --reload --port 8000
```

- Base URL: `http://127.0.0.1:8000/api/v1`
- Documentación interactiva: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

Variables de entorno:

| Variable | Valor por defecto | Uso |
|---|---|---|
| `DB_PATH` | `evidencias/api.db` | Ruta de la base SQLite. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000` | Orígenes permitidos para la interfaz de la semana 3. |

Reiniciar los datos de prueba:

```powershell
python -m persistencia.inicializar_db
```

> La base de la API es independiente de `evidencias/prueba.db` para no alterar
> las evidencias de la semana 13.

## 5. Contratos

Resumen (detalle completo, ejemplos y errores en
[`docs/contratos_api.md`](docs/contratos_api.md)):

| RF | Método y ruta | Éxito | Errores |
|---|---|---|---|
| RF-05 | `POST /api/v1/mascotas` | `201` ficha creada | `400` ERR-004, `404` ERR-008, `409` ERR-009 |
| RF-05 | `PUT /api/v1/mascotas/{id}` | `200` ficha actualizada | `400` ERR-004, `403` ERR-003, `404` ERR-011 |
| RF-05 | `DELETE /api/v1/mascotas/{id}?refugio_id={id}` | `204` sin cuerpo | `400` ERR-004, `403` ERR-003, `404` ERR-011 |
| RF-34 | `GET /api/v1/mascotas` | `200` página del catálogo | `400` ERR-004 |

Formato de error:

```json
{ "detail": "mensaje legible", "codigo": "ERR-004" }
```

| Código | HTTP | Significado |
|---|---|---|
| `ERR-003` | `403` | La ficha no pertenece al refugio indicado |
| `ERR-004` | `400` | Datos de entrada inválidos |
| `ERR-006` | `409` | Violación de integridad de la base |
| `ERR-008` | `404` | El refugio no existe |
| `ERR-009` | `409` | El refugio no está verificado |
| `ERR-011` | `404` | La ficha no existe |

> **Actor temporal:** la autenticación y los roles se integran en la semana 3.
> Hasta entonces, el refugio se envía como `refugio_id` en el cuerpo (POST/PUT)
> o en la consulta (DELETE).

## 6. Pruebas funcionales

```powershell
python -m pytest -v
```

Resultado: **39/39 pruebas pasan** en ~1,6 s
(`evidencias/salida_pruebas_semana14.txt`). Aparece un aviso de deprecación de
Starlette sobre `httpx`; no afecta los resultados.

| RF | Escenario | Acción | Resultado obtenido | Evidencia |
|---|---|---|---|---|
| RF-05 | Válido | `POST` con refugio verificado y 2 fotos | `201`, id 7, `disponible`, 2 fotos; verificado en SQLite desde otra conexión | `test_rf05_api.py`, `demo_api.txt` |
| RF-05 | Rechazo | `POST` con refugio no verificado | `409` ERR-009; 0 filas nuevas | `test_rf05_api.py` |
| RF-05 | Entrada | `POST` con especie inválida | `400` ERR-004; 0 filas nuevas | `test_rf05_api.py`, `test_rnf10_integridad.py` |
| RF-05 | Edición | `PUT` de ficha incompleta con una foto | `200`; pasa a `disponible` y aparece en el catálogo | `test_rf05_api.py` |
| RF-05 | Baja | `DELETE` de una ficha propia | `204`; estado `baja` y ya no aparece en el catálogo | `test_rf05_api.py` |
| RF-34 | Válido | `GET` del catálogo inicial | `200`, total 3, orden `[1, 3, 2]` | `test_rf34_api.py`, `demo_api.txt` |
| RF-34 | Filtros | Especie, tamaño y rango de edad | `[1, 3]`, `[2]`, `[2]` | `test_rf34_api.py` |
| RF-34 | Paginación | `por_pagina=2` | Página 1 `[1, 3]`; página 2 `[2]`; total 3 | `test_rf34_api.py` |
| RF-34 | Ausencia | Filtro válido sin coincidencias | `200`, total 0, lista vacía | `test_rf34_api.py`, `demo_api.txt` |
| RF-34 | Entrada | `especie=conejo` | `400` ERR-004 | `test_rf34_api.py`, `demo_api.txt` |

Demostración por HTTP real (Uvicorn + httpx), con peticiones y respuestas
completas:

```powershell
python -m pruebas.demo_api
```

Genera `evidencias/demo_api.txt`: crea, consulta, actualiza, da de baja y
verifica que la ficha dada de baja sale del catálogo.

## 7. RNF y evidencias (matriz RF–RNF)

| RF / RNF | Calidad ISO/IEC 25010:2023 | Prueba y meta | Resultado | Evidencia |
|---|---|---|---|---|
| RF-05, RF-34 / **RNF-05** | Eficiencia de desempeño / comportamiento temporal | 1.000 fichas; 20 consultas consecutivas por HTTP; cada una ≤ 1 s | **20/20**; promedio 2,78 ms; p95 3,01 ms; máximo 3,05 ms | `evidencias/rnf_desempeno.txt` |
| RF-05, RF-34 / **RNF-08** | Mantenibilidad / capacidad para ser probado | Doble del repositorio, sin base real; cobertura ≥ 70 % en servicios | **9/9** pruebas aisladas; **100 %** de cobertura en `servicios/` | `test_servicios_aislados.py`, `evidencias/cobertura.txt` |
| RF-05, RF-34 / **RNF-10** | Seguridad / integridad | Matriz de entradas inválidas; 0 filas persistidas | **14/14** casos rechazados; 0 filas nuevas o modificadas | `test_rnf10_integridad.py`, `salida_pruebas_semana14.txt` |
| RF-05, RF-34 / **RNF-04** | Seguridad / confidencialidad | Revisar claves del catálogo y la ficha pública | **0** campos personales | `test_rf34_api.py`, `demo_api.txt` |
| RF-34 / **RNF-07** | Flexibilidad / escalabilidad | 2.000 fichas y 5.000 adoptantes; p95 ≤ 1 s | **Pendiente** para la semana 3 | — |

Comandos de las verificaciones:

```powershell
# RNF-08: cobertura de los servicios
python -m coverage run -m pytest -q
python -m coverage report -m

# RNF-05: 1.000 fichas y 20 consultas por HTTP real
python -m pruebas.rnf_desempeno
```

**Lectura honesta del RNF-05:** la meta de la plantilla incluye 500 fichas y 50
usuarios concurrentes. Aquí se usó un volumen mayor (1.000 fichas) pero la
medición es **secuencial**, no concurrente. Por eso el resultado se declara
**cumplido en lo secuencial** y la prueba de 50 usuarios queda para la semana 3.
No se rebajó el umbral: cada consulta se exigió ≤ 1 s.

## 8. Checklist de entrega

| Criterio | Cumple | Evidencia |
|---|---|---|
| Los dos RF mantienen prioridad y alcance de la semana 1 | Sí | Tabla de alcance y `plantilla/plantilla_13_1.pdf` |
| Ambos RF tienen servicios y endpoints identificables | Sí | `servicios/` y `api/main.py` |
| Los contratos describen éxito, entrada inválida y errores | Sí | `docs/contratos_api.md` y `/docs` |
| Hay resultado válido y rechazo/ausencia por cada RF | Sí | Tabla de la sección 6 |
| Se verifica persistencia real y ausencia de escrituras indebidas | Sí | Pruebas con SQLite y conteos antes/después |
| El SQL queda en persistencia y las reglas en servicio/dominio | Sí | Sección 3 y `repositorio.py` |
| Cada RF se vincula con sus RNF y atributos ISO | Sí | Sección 7 |
| Los RNF previstos tienen medidas y evidencias | Sí | RNF-04, 05, 08 y 10; RNF-07 pendiente |
| Se distinguen incumplimientos y pendientes de la semana 3 | Sí | Secciones 7 y 10 |
| El README permite ejecutar y repetir las pruebas | Sí | Comandos de las secciones 4, 6 y 7 |

## 9. Persistencia de la semana 13 (resumen)

El esquema se recrea desde cero con `schema.sql` + `seed.sql`:

- **`refugio`**: `id`, `nombre`, `localidad`, `estado_verificacion`.
- **`mascota`**: ficha completa, `refugio_id`, `estado` y `fecha_publicacion`.
- **`fotografia`**: `mascota_id`, `archivo`, `orden` (1 a 5, único por ficha).

Reglas implementadas: RN-22 (1 a 5 fotos para publicar), RN-03 (solo refugio
verificado) y RN-15 (adoptada o dada de baja no aparece en el catálogo). La
integridad se refuerza con CHECK, FK, índices, triggers y transacciones.

Estado inicial de la base de prueba:

| Mascota | Refugio | Especie / tamaño | Estado | ¿Catálogo? |
|---|---|---|---|---|
| 1 — Luna | 1 | perro / grande | disponible | Sí |
| 2 — Milo | 1 | gato / pequeño | disponible | Sí |
| 3 — Rocky | 1 | perro / mediano | disponible | Sí |
| 4 — Nube | 2 | gato / pequeño | disponible | No: refugio pendiente |
| 5 — Toby | 1 | perro / pequeño | incompleta | No: sin foto |
| 6 — Canela | 1 | perro / mediano | adoptada | No: adoptada |

Catálogo esperado: **Luna (1), Rocky (3), Milo (2)**.

Pruebas de persistencia (12/12):

```powershell
cd persistencia
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
python prueba_persistencia.py
```

Salida esperada: `RESUMEN: 12/12 pruebas pasaron`
(`evidencias/salida_pruebas.txt`).

## 10. Estado, pendientes y relevo a la semana 3

**Implementado y verificado en la semana 14**

- Servicios de aplicación de RF-05 y RF-34.
- API REST con cuatro endpoints, contratos, errores y CORS.
- 39 pruebas funcionales, de integridad y de servicios aislados.
- RNF-04, RNF-05 (secuencial), RNF-08 y RNF-10 con evidencia reproducible.
- Demostración HTTP real de ambos RF.

**Pendiente para la semana 3**

- Autenticación, roles y reemplazo de `refugio_id` explícito por el usuario autenticado.
- Pantalla de ficha y catálogo (React/Vite) contra esta API.
- Prueba de concurrencia de RNF-05 (50 usuarios) y RNF-07 (2.000 fichas, 5.000 adoptantes).
- Migración y verificación en PostgreSQL (ADR-03/ADR-10).
- Almacenamiento binario de fotos (hoy se guarda la ruta).
- Rechazo automático de solicitudes pendientes al dar de baja (RN-15), fuera de este corte.

**Relevo a la interfaz:** contratos en `docs/contratos_api.md`, origen CORS
`http://localhost:5173`, datos iniciales con `python -m persistencia.inicializar_db`
y RNF pendientes marcados en la sección 7.

## 11. Trazabilidad rápida

| Elemento | Dónde se evidencia |
|---|---|
| RF-05 | `servicios/servicio_mascotas.py`, `api/main.py` (POST/PUT/DELETE), `test_rf05_api.py` |
| RF-34 | `servicios/servicio_catalogo.py`, `api/main.py` (GET), `test_rf34_api.py` |
| Contratos | `docs/contratos_api.md`, `/docs` y `/openapi.json` |
| RNF-04 | `test_catalogo_sin_datos_personales_rnf04` |
| RNF-05 | `pruebas/rnf_desempeno.py` y `evidencias/rnf_desempeno.txt` |
| RNF-08 | `pruebas/test_servicios_aislados.py` y `evidencias/cobertura.txt` |
| RNF-10 | `pruebas/test_rnf10_integridad.py` y `evidencias/salida_pruebas_semana14.txt` |
| RNF-07 | Pendiente de la semana 3 |
| Persistencia | `persistencia/schema.sql`, `repositorio.py` y `salida_pruebas.txt` |
| Plantilla 13.1 | `plantilla/plantilla_13_1.pdf` y `plantilla/plantilla_13_1.tex` |

## 12. Documento de las semanas 13 y 14

[`docs/informe_semanas_13_14.md`](docs/informe_semanas_13_14.md) reúne en un
solo documento la persistencia de la semana 13 y los servicios, contratos,
pruebas y RNF de la semana 14. Es el texto de lectura continua de la entrega;
los detalles operativos están en el README y en
[`docs/contratos_api.md`](docs/contratos_api.md).

`plantilla/plantilla_13_1.tex` se mantiene como documento formal de la semana
13 (portada, alcance, priorización, matriz RF–RNF, fichas y checklist). Se
compila en Overleaf con **pdfLaTeX** y no requiere archivos adicionales. La
versión compilada está en `plantilla/plantilla_13_1.pdf`.
