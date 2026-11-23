# Corte vertical semanas 13–15 — Persistencia, servicios, API e interfaz de RF-05 y RF-34

Repositorio: <https://github.com/jrojasp11-maker/proyecto_arq_sis_mascotas>

Proyecto: **Sistema de Apoyo a la Decisión para la Adopción Responsable de Mascotas mediante Inteligencia Artificial**.

## Contexto y alcance

Este repositorio documenta el corte vertical de **Arquitectura de Sistemas I**
sobre el caso de estudio de **Práctica de Ingeniería**: los refugios publican
fichas de mascotas y los adoptantes consultan el catálogo. En estas entregas no se
implementa la inteligencia artificial.

| Semana | Trabajo | Evidencia |
|---|---|---|
| 13 | Persistencia de los dos RF priorizados | Esquema, repositorio y 12 pruebas |
| 14 | Servicios, API, contratos y verificación de RNF | API FastAPI, 39 pruebas y evidencias de calidad |
| **15** | **Interfaz mínima, integración con la API real y cierre de la matriz RF–RNF** | **Pantalla `/ui/`, 53 pruebas e integración verificada** |
| 3 (prototipo) | Autenticación, roles y PostgreSQL | Implementado: Supabase (`aqsis`), JWT por rol y verificación remota |

| Orden | RF | Resultado observable |
|---|---|---|
| 1 | **RF-05 — Gestión de la ficha de mascota** | El refugio crea, actualiza o da de baja una ficha; obtiene su `id` y su estado (`incompleta` o `disponible`). |
| 2 | **RF-34 — Consulta del catálogo** | El adoptante lista fichas disponibles con filtros por especie, tamaño y edad, con paginación y orden estable. |

**Stack:** Python 3.12 + FastAPI + Pydantic v2 + PostgreSQL en Supabase
(esquema `aqsis`) con SQLite 3 como modo local y de pruebas. El SQL está
encapsulado en `persistencia/repositorio.py` y `persistencia/repositorio_postgres.py`;
no se repite en la API. La autenticación usa JWT HS256 propio con roles
`refugio`, `adoptante` y `admin`. La interfaz mínima es HTML, CSS y JavaScript
servidos por la propia FastAPI en `/ui/`, sin framework adicional ni CORS nuevo.

## 1. Requisitos e instalación

- **Python 3.12.10** (probado con esta versión; funciona con 3.10 o superior).
- **SQLite 3.49.1** (incluido en Python; modo local sin servidor).
- **PostgreSQL en Supabase** con `DATABASE_URL` para el modo persistente.
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
├── frontend/
│   ├── index.html              # pantalla mínima de RF-05 y RF-34
│   ├── app.js                  # fetch a /api/v1, estados y mensajes
│   └── styles.css              # estilos y contraste de la interfaz
├── api/
│   ├── main.py                 # rutas, login, CORS, errores HTTP y /ui/
│   ├── esquemas.py             # contratos Pydantic (incluye Login)
│   └── dependencias.py         # selecciona PostgreSQL o SQLite
├── seguridad/
│   └── autenticacion.py        # PBKDF2, JWT HS256, roles y propietario
├── servicios/
│   ├── servicio_mascotas.py    # RF-05: crear, consultar, actualizar, baja
│   └── servicio_catalogo.py    # RF-34: listar y filtrar el catálogo
├── persistencia/
│   ├── schema.sql / seed.sql   # SQLite: tablas, índices, triggers y usuarios
│   ├── schema_postgres.sql     # PostgreSQL: esquema aqsis, índices y triggers
│   ├── seed_postgres.sql       # PostgreSQL: carga inicial y usuarios demo
│   ├── repositorio.py          # RepositorioMascotas (todo el SQL SQLite)
│   ├── repositorio_postgres.py # mismo contrato sobre Supabase
│   ├── migrar_supabase.py      # crea/verifica aqsis y hashea usuarios demo
│   ├── inicializar_db.py       # crea/reinicia la base local de la API
│   ├── prueba_persistencia.py  # 12 pruebas de la semana 13
│   └── demo_consulta.py        # consulta manual del catálogo
├── pruebas/
│   ├── test_autenticacion.py   # login, roles, JWT y propietario
│   ├── test_rf05_api.py        # pruebas funcionales de RF-05
│   ├── test_rf34_api.py        # pruebas funcionales de RF-34
│   ├── test_rnf10_integridad.py # matriz de entradas inválidas
│   ├── test_servicios_aislados.py # RNF-08 con doble de repositorio
│   ├── test_integracion_ui.py  # integración de /ui/ con los contratos
│   ├── rnf_desempeno.py        # RNF-05 secuencial por HTTP real
│   ├── rnf_escalabilidad.py    # RNF-05 concurrente y RNF-07
│   ├── rnf_supabase.py         # RNF-05/RNF-07 contra Supabase
│   ├── verificar_supabase.py   # verificación HTTP y EXPLAIN en Supabase
│   ├── demo_api.py             # demostración HTTP de ambos RF
│   ├── demo_integracion.py     # demostración reproducible de /ui/ + API
│   └── servidor.py             # Uvicorn temporal para las verificaciones
├── docs/
│   ├── contratos_api.md        # contratos completos de los endpoints
│   ├── informe_semanas_13_14.md # informe combinado de las semanas 13 y 14
│   └── informe_semana15.md     # informe de cierre de la semana 15
├── evidencias/
│   ├── salida_pruebas.txt      # 12 pruebas de persistencia (semana 13)
│   ├── salida_pruebas_semana14.txt # 39 pruebas de la semana 14
│   ├── salida_pruebas_semana15.txt # 44 pruebas de la semana 15
│   ├── salida_pruebas_supabase.txt # 53 pruebas con autenticación y roles
│   ├── cobertura.txt           # cobertura de servicios (RNF-08)
│   ├── rnf_desempeno.txt       # RNF-05 secuencial local
│   ├── rnf_escalabilidad.txt   # RNF-05 concurrente y RNF-07 locales
│   ├── rnf_supabase.txt        # RNF-05 y RNF-07 contra Supabase
│   ├── supabase_verificacion.txt # roles, RF y EXPLAIN en PostgreSQL
│   ├── demo_api.txt            # peticiones y respuestas HTTP reales
│   ├── integracion_ui.txt      # escenarios de integración de la interfaz
│   ├── pantalla_ui.txt         # recorrido en navegador real
│   ├── prueba.db               # base de la semana 13
│   └── api.db / demo_api.db / rnf_desempeno.db / integracion_ui.db # bases locales (no versionadas)
└── plantilla/
    ├── plantilla_13_1.tex      # documento formal de la semana 13
    ├── plantilla_13_1.pdf      # versión compilada
    ├── plantilla_13_14.tex     # informe formal de las semanas 13 y 14
    └── plantilla_13_14.pdf     # versión compilada
```

## 3. Arquitectura y responsabilidades

Flujo completo del corte vertical:

```text
Interfaz (/ui/) -> HTTP + JWT -> API (/api/v1) -> Servicio de aplicación -> Repositorio -> SQLite o PostgreSQL/Supabase
```

| Capa | Dónde | Responsabilidad |
|---|---|---|
| Interfaz | `frontend/` | Mostrar los dos RF, iniciar sesión, conservar entradas y reflejar estados; envía el JWT en la cabecera `Authorization`. El token vive solo en memoria. |
| Seguridad | `seguridad/autenticacion.py` | Verificar contraseñas PBKDF2, firmar JWT HS256, exigir roles y comprobar el refugio propietario. |
| API | `api/main.py` | Recibir HTTP, autenticar, validar la forma, delegar y traducir errores. No contiene reglas ni SQL. |
| Servicio | `servicios/` | Coordinar el caso de uso, normalizar la respuesta y decidir la ausencia de una ficha. |
| Repositorio | `persistencia/` | Todo el SQL, las validaciones de dominio y las transacciones en SQLite o PostgreSQL. |
| Base de datos | SQLite / Supabase | `refugio`, `mascota`, `fotografia` y `usuario`, con CHECK, FK, índices y triggers. |

Esto permite probar los servicios con un doble del repositorio (RNF-08) sin abrir
una base real, y mantener el SQL fuera de la API. La interfaz se sirve desde el
mismo proceso y origen que la API, por lo que usa rutas relativas y no depende de
CORS.

## 4. Ejecutar la API y la interfaz

```powershell
# 1) Crear o reiniciar la base con el estado inicial conocido
python -m persistencia.inicializar_db

# 2) Levantar la API (sirve también la interfaz)
uvicorn api.main:app --reload --port 8000
```

- Base URL: `http://127.0.0.1:8000/api/v1`
- **Interfaz mínima: `http://127.0.0.1:8000/ui/`**
- Documentación interactiva: `http://127.0.0.1:8000/docs`
- OpenAPI: `http://127.0.0.1:8000/openapi.json`

La pantalla está organizada en tres pestañas —**Crear ficha (RF-05)**,
**Editar y baja (RF-05)** y **Consultar catálogo (RF-34)**— y tiene un botón
**Rellenar datos de ejemplo** que carga automáticamente una ficha válida, los
datos de edición y los filtros del catálogo. El relleno solo prepara los campos:
no llama a la API ni simula respuestas; cada resultado sigue viniendo del
servidor. Tras crear, el `id` real queda listo en la pestaña de edición.

Variables de entorno:

| Variable | Valor por defecto | Uso |
|---|---|---|
| `DATABASE_URL` | Sin valor | DSN de PostgreSQL/Supabase. Si existe, se usa el esquema `aqsis`; si no, se usa `DB_PATH`. **Secreto: no versionar**. |
| `AUTH_JWT_SECRET` | Valor fijo solo en desarrollo local | Secreto HS256. Obligatorio cuando hay `DATABASE_URL` o `VERCEL`. **Secreto: no versionar**. |
| `DB_PATH` | `evidencias/api.db` | Ruta de la base SQLite cuando no hay `DATABASE_URL`. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000` | Orígenes permitidos para una interfaz externa futura; `/ui/` comparte origen con la API. |

Para preparar Supabase en local, coloque `DATABASE_URL` y `AUTH_JWT_SECRET` en
`.env.local` (excluido de Git) y ejecute:

```powershell
python -m persistencia.migrar_supabase
python -m pruebas.verificar_supabase
```

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
| Autenticación | `POST /api/v1/auth/token` | `200` `access_token`, `token_type`, `rol`, `refugio_id`, `expires_in` | `401` ERR-401 |
| RF-05 | `POST /api/v1/mascotas` | `201` ficha creada | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-008, `409` ERR-009 |
| RF-05 | `PUT /api/v1/mascotas/{id}` | `200` ficha actualizada | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-011 |
| RF-05 | `DELETE /api/v1/mascotas/{id}?refugio_id={id}` | `204` sin cuerpo | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-011 |
| RF-34 | `GET /api/v1/mascotas` | `200` página del catálogo | `400` ERR-004, `401` ERR-401 |

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
| `ERR-401` | `401` | Token ausente, inválido o expirado; credenciales incorrectas |
| `ERR-403` | `403` | El rol no puede ejecutar la operación |

Todas las rutas anteriores conservan sus nombres y claves JSON. El campo
`refugio_id` sigue presente por compatibilidad en POST/PUT/DELETE, pero la API
verifica que coincida con el token (o que el actor sea `admin`). `GET
/api/v1/mascotas` acepta cualquiera de los tres roles. El login es el único
endpoint nuevo.

Usuarios demo: `refugio` (refugio 1), `adoptante` y `admin`. La credencial de
demostración se gestiona fuera del repositorio y no se muestra en documentos,
evidencias ni mensajes de commit. Las contraseñas se guardan hasheadas con
PBKDF2-HMAC-SHA256.

## 6. Pruebas funcionales e integración

```powershell
python -m pytest -v
```

Resultado: **53/53 pruebas pasan** en ~7 s
(`evidencias/salida_pruebas_supabase.txt`). Incluye 9 pruebas de autenticación y
roles además de las 44 anteriores. Aparece un aviso de deprecación de Starlette
sobre `httpx`; no afecta los resultados.

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

### Integración desde la interfaz (semana 15)

La pantalla `/ui/` envía las solicitudes de los contratos vigentes mediante
`fetch`; no simula respuestas ni guarda el resultado en el navegador. Para
reproducir los escenarios con HTTP real:

```powershell
python -m pruebas.demo_integracion
```

Genera `evidencias/integracion_ui.txt`: interfaz servida, creación con `id`
real, rechazos `ERR-004`/`ERR-009`, edición, baja, paginación, ausencia, persistencia
tras reiniciar el backend y fallo de comunicación. `evidencias/pantalla_ui.txt`
registra el mismo recorrido ejecutado en un navegador real.

| Escenario desde la pantalla | Resultado observable |
|---|---|
| Consultar catálogo, crear ficha y recargar | ids `[1, 3, 2]` → creación id `7` → ids `[1, 3, 2, 7]` desde la API |
| Editar y dar de baja el id `7` | `200` con nombre actualizado; `204`; ids `[1, 3, 2]` |
| Ausencia y entrada inválida | `total 0` con tabla vacía; `400 ERR-004` con mensaje orientador |
| Rechazo de negocio al crear | `409 ERR-009`; el nombre escrito se conserva |
| Backend detenido | Mensaje de "resultado no confirmado", sin reintento ni éxito falso; tabla limpiada |

El detalle de los 13 escenarios y la matriz RF–RNF final están en
[`docs/informe_semana15.md`](docs/informe_semana15.md).

## 7. RNF y evidencias (matriz RF–RNF final)

| RF / RNF | Característica ISO/IEC 25010:2023 | Prueba y meta | Resultado | Estado | Evidencia |
|---|---|---|---|---|---|
| RF-05, RF-34 / **RNF-04** | Seguridad / confidencialidad | Revisar claves del catálogo y la ficha pública | **0** campos personales | **Cumple** | `test_rf34_api.py`, `demo_api.txt` |
| RF-05, RF-34 / **RNF-05** | Eficiencia de desempeño / comportamiento temporal | 1.000 fichas; 20 consultas consecutivas (cada una ≤ 1 s) y 50 usuarios concurrentes × 20 consultas (p95 ≤ 1 s) | Local: secuencial **20/20**, p95 3,78 ms; concurrente **1000/1000**, p95 413,45 ms. Supabase: secuencial **20/20**, p95 107,66 ms; concurrente **1000/1000**, p95 731,45 ms | **Cumple** | `pruebas/rnf_desempeno.py`, `pruebas/rnf_escalabilidad.py`, `pruebas/rnf_supabase.py` y sus tres evidencias |
| RF-05, RF-34 / **RNF-08** | Mantenibilidad / capacidad para ser probado | Doble del repositorio, sin base real; cobertura ≥ 70 % en servicios | **9/9** pruebas aisladas; **100 %** de cobertura en 33 sentencias | **Cumple** | `test_servicios_aislados.py`, `evidencias/cobertura.txt` |
| RF-05, RF-34 / **RNF-10** | Seguridad / integridad | Matriz de entradas inválidas; 0 filas persistidas | **14/14** casos rechazados; 0 filas nuevas o modificadas | **Cumple** | `test_rnf10_integridad.py`, `salida_pruebas_semana14.txt` |
| RF-34 / **RNF-07** | Flexibilidad / escalabilidad | 2.000 fichas y 5.000 adoptantes simulados como consultas; p95 ≤ 1 s | Local: **5000/5000**, p95 465,19 ms. Supabase: **5000/5000**, p95 494,45 ms | **Cumple** | `pruebas/rnf_escalabilidad.py`, `pruebas/rnf_supabase.py`, `evidencias/rnf_escalabilidad.txt`, `evidencias/rnf_supabase.txt` |

Comandos de las verificaciones:

```powershell
# RNF-08: cobertura de los servicios (se repite en la semana 15)
python -m coverage run -m pytest -q
python -m coverage report -m

# RNF-05: 1.000 fichas y 20 consultas secuenciales por HTTP real
python -m pruebas.rnf_desempeno

# RNF-05 con 50 usuarios concurrentes y RNF-07 con 2.000 fichas / 5.000 consultas
python -m pruebas.rnf_escalabilidad

# Las mismas dos cargas contra PostgreSQL/Supabase
python -m pruebas.rnf_supabase
```

**Lectura honesta de los RNF:** en secuencial se conservó el criterio más
estricto (cada consulta ≤ 1 s, 20/20). Bajo carga se usa el criterio p95 ≤ 1 s.
Las mediciones locales dieron p95 413,45 ms (RNF-05 concurrente) y 465,19 ms
(RNF-07). Contra Supabase, con latencia de red real (~95 ms por ida y vuelta),
dieron p95 731,45 ms y 494,45 ms; ambas por debajo del umbral. Para lograrlo,
el repositorio PostgreSQL usa una sola consulta con `COUNT(*) OVER()`,
desactiva el `pool_pre_ping` y los prepared statements del pooler, y ejecuta las
lecturas en `AUTOCOMMIT`. El rol `adoptante` existe desde la semana 15 y cada
adoptante se representa con una consulta autenticada al catálogo (RF-34) contra
la API real. No se simulan respuestas y no queda ningún RNF sin medir.

## 8. Checklist de entrega

| Criterio | Cumple | Evidencia |
|---|---|---|
| Los dos RF mantienen prioridad y alcance de la semana 1 | Sí | Tabla de alcance y `plantilla/plantilla_13_1.pdf` |
| Ambos RF tienen servicios y endpoints identificables | Sí | `servicios/` y `api/main.py` |
| Los contratos describen éxito, entrada inválida y errores | Sí | `docs/contratos_api.md` y `/docs` |
| La interfaz ejecuta ambos RF contra la API real | Sí | `/ui/` y `evidencias/pantalla_ui.txt` |
| Hay resultado válido y rechazo/ausencia por cada RF | Sí | Secciones 6 y `evidencias/integracion_ui.txt` |
| Se verifica persistencia real y ausencia de escrituras indebidas | Sí | Recarga, conexión nueva y reinicio del backend |
| Los fallos de comunicación no confirman resultados no verificados | Sí | `pantalla_ui.txt` y `test_integracion_ui.py` |
| El SQL queda en persistencia y las reglas en servicio/dominio | Sí | Sección 3 y `repositorio.py` |
| Cada RF se vincula con sus RNF y atributos ISO | Sí | Sección 7 |
| La matriz final distingue cumplidos, parciales y no verificados | Sí | Sección 7: todos los RNF medidos; no quedan no verificados |
| Autenticación por rol y PostgreSQL quedan implementados y verificados | Sí | Secciones 4, 7 y 10 |
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

## 10. Estado, cierre y pendientes

**Implementado y verificado en la semana 15**

- Interfaz mínima en `/ui/` con pestañas, relleno automático, manejo de estados
  y mensajes comprensibles; los fallos de comunicación no confirman resultados.
- Autenticación básica por rol (`refugio`, `adoptante`, `admin`) con login en
  `/api/v1/auth/token`, JWT HS256 y contraseñas hasheadas con PBKDF2.
- PostgreSQL en Supabase, esquema separado `aqsis`, índices y triggers
  verificados con `EXPLAIN`; SQLite se conserva como modo local y de pruebas.
- Sin cambios en rutas ni claves JSON documentadas; `refugio_id` se conserva y
  se valida contra el token.
- 53/53 pruebas, cobertura 100 % en servicios y verificación HTTP real contra
  Supabase (`evidencias/supabase_verificacion.txt`).
- RNF-05 y RNF-07 medidos tanto en local como contra Supabase; ambos cumplen.

**Implementado en las semanas 13 y 14**

- Esquema, repositorio, servicios de RF-05 y RF-34, API REST, contratos,
  traducción de errores y CORS.
- RNF-04, RNF-08 y RNF-10 con evidencia; RNF-05 y RNF-07 medidos por HTTP real.

**Pendiente fuera de este corte**

- Almacenamiento binario de fotos (hoy se guarda el nombre de archivo).
- Rechazo automático de solicitudes pendientes al dar de baja (RN-15).
- Ampliación de la interfaz sin convertirla en un portal; la pantalla ya cubre
  los dos RF del corte.

**Estado final:** contratos en `docs/contratos_api.md`, interfaz en `/ui/`,
datos iniciales en SQLite con `python -m persistencia.inicializar_db` y datos
persistentes en Supabase con `python -m persistencia.migrar_supabase`. La URL
pública es <https://aqsis-corte-vertical.vercel.app/ui/>.

## 11. Trazabilidad rápida

| Elemento | Dónde se evidencia |
|---|---|
| RF-05 | `servicios/servicio_mascotas.py`, `api/main.py` (POST/PUT/DELETE), `test_rf05_api.py` |
| RF-34 | `servicios/servicio_catalogo.py`, `api/main.py` (GET), `test_rf34_api.py` |
| Autenticación | `seguridad/autenticacion.py`, `api/main.py` (`/auth/token`) y `pruebas/test_autenticacion.py` |
| PostgreSQL | `persistencia/schema_postgres.sql`, `repositorio_postgres.py`, `migrar_supabase.py` y `evidencias/supabase_verificacion.txt` |
| Interfaz | `frontend/index.html`, `frontend/app.js`, `frontend/styles.css` y `/ui/` en `api/main.py` |
| Integración UI | `pruebas/test_integracion_ui.py`, `pruebas/demo_integracion.py`, `evidencias/integracion_ui.txt` y `evidencias/pantalla_ui.txt` |
| Contratos | `docs/contratos_api.md`, `/docs` y `/openapi.json` |
| RNF-04 | `test_catalogo_sin_datos_personales_rnf04` |
| RNF-05 | `pruebas/rnf_desempeno.py`, `pruebas/rnf_escalabilidad.py` y sus dos evidencias |
| RNF-08 | `pruebas/test_servicios_aislados.py` y `evidencias/cobertura.txt` |
| RNF-10 | `pruebas/test_rnf10_integridad.py` y `evidencias/salida_pruebas_semana14.txt` |
| RNF-07 | `pruebas/rnf_escalabilidad.py` y `evidencias/rnf_escalabilidad.txt` |
| Persistencia | `persistencia/schema.sql`, `repositorio.py` y `salida_pruebas.txt` |
| Plantilla 13.1 | `plantilla/plantilla_13_1.pdf` y `plantilla/plantilla_13_1.tex` |
| Informe 13 y 14 | `docs/informe_semanas_13_14.md`, `plantilla/plantilla_13_14.tex` y `plantilla/plantilla_13_14.pdf` |
| Informe 15 | `docs/informe_semana15.md` |

## 12. Documentos de las semanas 13 a 15

[`docs/informe_semanas_13_14.md`](docs/informe_semanas_13_14.md) reúne en un
solo documento la persistencia de la semana 13 y los servicios, contratos,
pruebas y RNF de la semana 14. Es el texto de lectura continua de esa entrega;
los detalles operativos están en el README y en
[`docs/contratos_api.md`](docs/contratos_api.md).

[`docs/informe_semana15.md`](docs/informe_semana15.md) cierra el corte: describe
la interacción de los dos RF, la conexión con los contratos vigentes, los 13
escenarios de integración, la matriz RF–RNF final, el checklist y las
limitaciones. Todos los RNF quedan **cumplidos con evidencia reproducible**:
RNF-05 en secuencial y con 50 usuarios concurrentes, y RNF-07 con 2.000 fichas
y 5.000 consultas.

`plantilla/plantilla_13_1.tex` se mantiene como documento formal de la semana
13 (portada, alcance, priorización, matriz RF–RNF, fichas y checklist). Se
compila en Overleaf con **pdfLaTeX** y no requiere archivos adicionales. La
versión compilada está en `plantilla/plantilla_13_1.pdf`.

El informe combinado también tiene versión formal en
[`plantilla/plantilla_13_14.tex`](plantilla/plantilla_13_14.tex), con el mismo
estilo, y su PDF compilado en
[`plantilla/plantilla_13_14.pdf`](plantilla/plantilla_13_14.pdf). Se compila
con **pdfLaTeX** en Overleaf sin archivos adicionales.

El cierre de las semanas 13 a 15, incluida la autenticación por rol y la
migración a Supabase, está en
[`plantilla/plantilla_13_14_15.tex`](plantilla/plantilla_13_14_15.tex). Es un
documento autocontenido y se compila con **pdfLaTeX** en Overleaf; allí debe
compilarse para generar su PDF de entrega.
