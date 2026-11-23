# Informe de la semana 15 — Interfaz, autenticación por rol e integración con Supabase

**Proyecto:** Sistema de Apoyo a la Decisión para la Adopción Responsable de Mascotas mediante Inteligencia Artificial.

**Asignatura:** Arquitectura de Sistemas I.

**Integrantes:** Juan Diego Rojas y Adrián Camaño.

**Fecha:** 20 de noviembre de 2026.

**Repositorio:** <https://github.com/jrojasp11-maker/proyecto_arq_sis_mascotas>

---

## 1. Resultado de la semana

Los dos requisitos funcionales priorizados se ejecutan desde una interfaz que consume la **API real**, sin simular respuestas. La pantalla no guarda el resultado en el navegador: cada dato visible se obtiene con una petición HTTP a `/api/v1`, ahora autenticada con un JWT por rol. El corte también quedó migrado a **PostgreSQL en Supabase** (esquema `aqsis`), conservando SQLite como modo local y de pruebas.

| RF | Prioridad | Acción desde la interfaz | Resultado observable |
|---|---|---|---|
| **RF-05** | 1 | Crear, editar y dar de baja una ficha | `id` real devuelto por la API, estado `disponible`/`incompleta`, confirmación HTTP `201`/`200`/`204` |
| **RF-34** | 2 | Consultar el catálogo con filtros y paginación | Lista recuperada del servidor con `total`, `pagina`, `por_pagina` y filas reales |

La interfaz se sirve desde la propia FastAPI en `/ui/`, en el **mismo origen** que la API. Por eso no fue necesario cambiar la configuración de CORS ni agregar dependencias de frontend.

La pantalla se organiza en tres pestañas —**Crear ficha (RF-05)**, **Editar y baja (RF-05)** y **Consultar catálogo (RF-34)**— con navegación por teclado. El botón **Rellenar datos de ejemplo** carga automáticamente una ficha válida, los datos de edición y los filtros del catálogo para acelerar la demostración. El relleno no consulta ni simula la API: solo prepara los campos; el `id`, el estado y las filas visibles siguen viniendo del servidor.

```text
Interfaz (/ui/)  →  API (/api/v1) + JWT  →  Servicio de aplicación  →  Repositorio  →  SQLite / PostgreSQL (Supabase)
```

Los identificadores, prioridades, reglas RN-22/RN-03/RN-15, formatos y contratos de las semanas 13 y 14 se conservan sin cambios.

### Autenticación por rol y Supabase

Se agregó `POST /api/v1/auth/token`, el único endpoint nuevo. Devuelve
`access_token`, `token_type`, `rol`, `refugio_id` y `expires_in`. Los roles son
`refugio`, `adoptante` y `admin`; las contraseñas se guardan con
PBKDF2-HMAC-SHA256 y el token se firma con JWT HS256 usando `AUTH_JWT_SECRET`.
El token se conserva solo en memoria en el navegador y se envía como
`Authorization: Bearer <token>` en cada petición.

- `GET /api/v1/mascotas`: cualquier rol autenticado.
- `POST`, `PUT` y `DELETE` de fichas: solo `refugio` y `admin`; `refugio` únicamente
  sobre su `refugio_id`, `admin` sobre cualquier refugio.
- Las rutas, los nombres de las claves JSON y los códigos `ERR-004`, `ERR-008`,
  `ERR-009` y `ERR-011` no cambiaron. Se suman `ERR-401` y `ERR-403`.

La base persistente es PostgreSQL en Supabase, en el esquema independiente
`aqsis` con tablas `refugio`, `mascota`, `fotografia` y `usuario`, índices
`idx_mascota_catalogo` e `idx_mascota_filtros` y los tres triggers de negocio.
`evidencias/supabase_verificacion.txt` registra la verificación HTTP de roles,
RF-05, RF-34 y el `EXPLAIN` que confirma el uso del índice del catálogo.

---

## 2. Actividad 1 — Interacción de los dos RF

| RF | Campos y acción | Resultado visible | Corrección ante error |
|---|---|---|---|
| RF-05 · crear | Refugio, nombre, raza, especie, edad, tamaño, energía, experiencia, fechas, fotos, historial y dos casillas; botón **Crear ficha** | Mensaje con `id`, estado y número de fotos devueltos por la API; el `id` se copia al panel de edición | El mensaje indica el código `ERR-004`, `ERR-008` o `ERR-009` y el detalle; los campos se conservan |
| RF-05 · editar/baja | `id` real, refugio dueño y nuevo nombre; botones **Actualizar nombre** y **Dar de baja** | Nombre y estado devueltos por `PUT`; confirmación HTTP `204` en la baja | Se muestran `ERR-003`, `ERR-011` o `ERR-004` según corresponda; no se afirma éxito sin respuesta |
| RF-34 · consultar | Especie, tamaño, edad mínima/máxima, página y por página; botón **Consultar catálogo** | Tabla con los datos recuperados y resumen `total`, `pagina`, `por_pagina` | Si `total = 0`, mensaje de ausencia y tabla vacía; si `400`, mensaje con `ERR-004` y orientación |

Prácticas de interacción aplicadas: etiquetas visibles, campos obligatorios marcados con `*`, selección para dominios cerrados, controles operables con teclado, mensajes de texto que no dependen del color, `aria-live="polite"` en los resultados y conservación de las entradas tras un rechazo. No se declara un RNF de accesibilidad nuevo: son prácticas básicas, no una verificación sustituta.

### Estados de cada acción

| Estado | RF-05 crear/editar/baja | RF-34 consultar |
|---|---|---|
| Inicial | Botones habilitados, sin mensaje | Botón habilitado, tabla vacía |
| En curso | Texto `Enviando...`, botón deshabilitado | Texto `Consultando...`, tabla limpiada, botón deshabilitado |
| Resultado | Mensaje de éxito con datos reales de la respuesta | Mensaje con total/página y filas reales |
| Rechazo | Mensaje con HTTP y código del contrato; entradas conservadas | Mensaje con `ERR-004`; tabla sin datos anteriores |
| Fallo de comunicación | Mensaje de "resultado no confirmado", sin reintento automático | Mensaje de servidor no disponible, tabla limpiada |

Un error `5xx` se trata como fallo de comunicación, no como resultado de negocio. Nunca se muestra un éxito falso y los controles se rehabilitan al finalizar el intento.

---

## 3. Actividad 2 — Conexión con los contratos vigentes

| RF | Solicitud que envía la interfaz | Tratamiento de la respuesta |
|---|---|---|
| RF-05 crear | `POST /api/v1/mascotas` con JSON `snake_case`: `refugio_id`, `nombre`, `raza`, `especie`, `edad_meses`, `tamano`, `nivel_energia`, `experiencia_requerida`, `apta_con_menores`, `apta_con_mascotas`, `historial_salud`, `historial_comportamiento`, `fecha_publicacion` (`AAAA-MM-DD`) y `fotografias` | `201`: muestra `id` y `estado` reales; `409 ERR-009`: refugio no verificado; `400 ERR-004`: datos inválidos; `404 ERR-008`: refugio ausente |
| RF-05 editar | `PUT /api/v1/mascotas/{id}` con `refugio_id` y `nombre` | `200`: nombre y estado reales; `403 ERR-003`, `404 ERR-011`, `400 ERR-004` |
| RF-05 baja | `DELETE /api/v1/mascotas/{id}?refugio_id={id}`, sin cuerpo | `204`: baja confirmada; `403 ERR-003`, `404 ERR-011` |
| RF-34 consultar | `GET /api/v1/mascotas?especie=...&tamano=...&edad_min=...&edad_max=...&pagina=...&por_pagina=...` | `200`: tabla desde `mascotas` y resumen; `400 ERR-004`: filtro inválido; `total = 0`: ausencia, no error |

No se cambió ningún contrato de los RF. El `id` lo genera el backend y el estado inicial lo decide el repositorio según RN-22 y RN-03. La interfaz solo valida la presencia de campos obligatorios y el formato visible de la fecha; las reglas de negocio siguen en el backend. Todas las solicitudes incluyen la cabecera `Authorization` obtenida en `/api/v1/auth/token`; el campo `refugio_id` se mantiene y se contrasta con el token.

La adaptación frente al ejemplo de citas de la guía es directa: allí se consulta por `id` de cita; aquí **RF-34 es un catálogo**, así que la verificación tras recargar se hace volviendo a consultar con filtros y comprobando que el `id` creado aparece en la respuesta del servidor.

---

## 4. Actividad 3 — Escenarios de integración ejecutados

Base inicial: seis mascotas sembradas; catálogo inicial `[1, 3, 2]`. Refugio `1` verificado y refugio `2` pendiente. Fecha usada en la demo: `2026-11-20`.

| # | RF | Escenario | Entrada / acción desde pantalla | Resultado esperado | Obtenido | Evidencia |
|---|---|---|---|---|---|---|
| 1 | RF-34 | Válido | Consultar sin filtros | `200`, total 3, orden `[1, 3, 2]` | `200`, total 3, ids `1,3,2` | `pantalla_ui.txt`, `integracion_ui.txt` |
| 2 | RF-05 | Válido | Crear ficha en refugio 1 con 2 fotos | `201`, id real, `disponible`, persistida | `201`, id `7`, `disponible`, 2 fotos | `pantalla_ui.txt` |
| 3 | RF-34 | Persistencia tras recarga | Recargar `/ui/` y volver a consultar | El id `7` aparece desde la API | total 4, ids `1,3,2,7` | `pantalla_ui.txt` |
| 4 | RF-05 | Edición | `PUT` con el id `7` y nuevo nombre | `200`, nombre actualizado | `200`, `Nala actualizada` | `pantalla_ui.txt` |
| 5 | RF-05 | Baja | `DELETE` del id `7` | `204` y ausencia en el catálogo | `204`; ids `1,3,2` | `pantalla_ui.txt` |
| 6 | RF-34 | Filtros | `especie=perro`, `tamano=mediano` | Solo perros medianos | ids `3,7` antes de la baja | `integracion_ui.txt` |
| 7 | RF-34 | Paginación | `por_pagina=2`, páginas 1 y 2 | Páginas distintas, total estable | p1 `[1,3]`, p2 `[2,7]`, total 4 | `integracion_ui.txt` |
| 8 | RF-34 | Ausencia | `gato` + `grande` | `200`, total 0, tabla vacía | `200`, total 0, 0 filas | `pantalla_ui.txt` |
| 9 | RF-34 | Entrada inválida | `especie=conejo` | `400 ERR-004` | `400 ERR-004`, tabla limpiada | `pantalla_ui.txt` |
| 10 | RF-05 | Rechazo de negocio | Crear en refugio 2 | `409 ERR-009`, sin filas nuevas | `409 ERR-009`, nombre conservado | `pantalla_ui.txt` |
| 11 | RF-05 | Entrada inválida | Crear con `especie=conejo` | `400 ERR-004` | `400 ERR-004`, sin filas nuevas | `integracion_ui.txt` |
| 12 | Comunicación | Backend detenido | Consultar y crear | Aviso comprensible, sin éxito falso, controles habilitados | HTTP `502`; mensaje "resultado no confirmado"; tabla limpiada; botones activos | `pantalla_ui.txt` |
| 13 | Persistencia | Reinicio del backend | Consultar tras reiniciar | Estado de la baja conservado | Ficha `7` ausente | `integracion_ui.txt` |

La persistencia se comprobó además desde una conexión SQLite nueva y tras reiniciar Uvicorn, no solo en la memoria de la página. Para el rechazo se comparó el conteo de filas antes y después.

### Evidencias

| Archivo | Contenido |
|---|---|
| `evidencias/pantalla_ui.txt` | Mensajes visibles, filas de la tabla, rechazos y fallo de comunicación en navegador real |
| `evidencias/integracion_ui.txt` | Reproducción automática de los escenarios anteriores con HTTP real y SQLite |
| `evidencias/salida_pruebas_supabase.txt` | 53/53 pruebas, incluidas 9 de autenticación por rol |
| `evidencias/cobertura.txt` | Repetición de RNF-08: 100 % en servicios |
| `evidencias/rnf_desempeno.txt` | Repetición de RNF-05: 20/20 consultas dentro del umbral |
| `evidencias/rnf_escalabilidad.txt` | RNF-05 con 50 usuarios concurrentes y RNF-07 con 2.000 fichas / 5.000 consultas |
| `evidencias/supabase_verificacion.txt` | Roles, RF-05, RF-34, persistencia en `aqsis` y `EXPLAIN` del índice |
| `evidencias/rnf_supabase.txt` | RNF-05 y RNF-07 medidos por HTTP real contra Supabase |

---

## 5. Actividad 4 — Matriz de cierre RF–RNF

Se conservan los identificadores y escenarios de las semanas anteriores. No se incorporan RNF nuevos por haber construido la interfaz.

| RF / RNF | Característica ISO/IEC 25010:2023 y escenario | Meta | Resultado medido | Estado | Evidencia |
|---|---|---|---|---|---|
| RF-05, RF-34 / **RNF-04** | Seguridad / confidencialidad. El catálogo y la ficha pública no exponen datos personales del adoptante | 0 campos personales | 0 campos en las claves revisadas | **Cumple** | `test_rf34_api.py`, `demo_api.txt` |
| RF-34 / **RNF-05** | Eficiencia de desempeño / comportamiento temporal. 1.000 fichas; 20 consultas consecutivas y 50 usuarios concurrentes × 20 consultas | Secuencial: cada consulta ≤ 1 s. Concurrente: p95 ≤ 1 s | Local: 20/20, p95 3,78 ms; 1000/1000, p95 413,45 ms. Supabase: 20/20, p95 107,66 ms; 1000/1000, p95 731,45 ms | **Cumple** | `pruebas/rnf_desempeno.py`, `pruebas/rnf_escalabilidad.py`, `pruebas/rnf_supabase.py` y sus evidencias |
| RF-05, RF-34 / **RNF-08** | Mantenibilidad / capacidad para ser probado. Servicios con repositorio simulado, sin base real | Pruebas aisladas y cobertura ≥ 70 % | 9/9 pruebas aisladas; 100 % de cobertura (33 sentencias) | **Cumple** | `pruebas/test_servicios_aislados.py`, `evidencias/cobertura.txt` |
| RF-05, RF-34 / **RNF-10** | Seguridad / integridad. Matriz de entradas inválidas | 0 filas persistidas ante entrada inválida | 14/14 casos rechazados; 0 filas nuevas o modificadas | **Cumple** | `pruebas/test_rnf10_integridad.py`, `salida_pruebas_semana14.txt` |
| RF-34 / **RNF-07** | Flexibilidad / escalabilidad. 2.000 fichas y 5.000 adoptantes simulados como consultas, p95 ≤ 1 s | p95 ≤ 1 s | Local: 5000/5000, p95 465,19 ms. Supabase: 5000/5000, p95 494,45 ms | **Cumple** | `pruebas/rnf_escalabilidad.py`, `pruebas/rnf_supabase.py`, `evidencias/rnf_escalabilidad.txt`, `evidencias/rnf_supabase.txt` |

### Lectura honesta de los resultados

- RNF-05 se midió desde el cliente HTTP sobre la respuesta completa, no hasta pintar en pantalla. En secuencial se conservó el criterio estricto: cada consulta ≤ 1 s (20/20). La concurrencia se verificó por separado con 50 usuarios × 20 consultas sobre 1.000 fichas; allí el criterio aplicado es p95 ≤ 1 s. El resultado local fue 413,45 ms y el de Supabase 731,45 ms. No se rebajó el umbral.
- RNF-08 se repitió tras agregar autenticación y una ruta de base alternativa; los servicios no cambiaron y el aislamiento con doble del repositorio sigue en 100 %.
- RNF-07 quedó **verificado**: 5.000 consultas autenticadas sobre 2.000 fichas con 50 usuarios concurrentes dieron p95 465,19 ms en local y 494,45 ms en Supabase. El rol adoptante se modela como una consulta al catálogo (RF-34) contra la API real.
- Para cumplir el umbral con latencia remota, el repositorio PostgreSQL agrupa el total y la página en una sola consulta, evita el `pool_pre_ping` y los prepared statements del pooler, y usa lecturas en `AUTOCOMMIT`.
- Las prácticas de etiquetas, teclado y mensajes se aplicaron, pero no sustituyen un RNF de interacción acordado.

---

## 6. Reproducción

```powershell
python -m persistencia.inicializar_db
uvicorn api.main:app --reload --port 8000
```

- Interfaz: <http://127.0.0.1:8000/ui/>
- API: <http://127.0.0.1:8000/api/v1>
- Documentación: <http://127.0.0.1:8000/docs>

```powershell
python -m pytest -v
python -m coverage run -m pytest -q
python -m coverage report -m
python -m pruebas.demo_api
python -m pruebas.demo_integracion
python -m pruebas.rnf_desempeno
python -m pruebas.rnf_escalabilidad
```

Con `.env.local` que contenga `DATABASE_URL` y `AUTH_JWT_SECRET`:

```powershell
python -m persistencia.migrar_supabase
python -m pruebas.verificar_supabase
python -m pruebas.rnf_supabase
```

`demo_integracion` reinicia su propia base en `evidencias/integracion_ui.db` y genera `evidencias/integracion_ui.txt`; no altera la base de demostración manual.

---

## 7. Checklist final

| Criterio de la guía | Cumple | Evidencia |
|---|---|---|
| Ambos RF conservan alcance, prioridad e identificadores | Sí | Sección 1 y `docs/informe_semanas_13_14.md` |
| La interfaz permite ejecutar ambos RF mediante sus API reales | Sí | `/ui/` y `pantalla_ui.txt` |
| Los contratos coinciden con solicitudes y respuestas observadas | Sí | Sección 3 y `docs/contratos_api.md` |
| Se prueban éxito, rechazo o ausencia pertinentes de ambos RF | Sí | Sección 4, 13 escenarios |
| Se demuestra persistencia y se evita confirmar resultados simulados | Sí | Recarga, conexión nueva y reinicio del backend |
| Se manejan errores de entrada y comunicación de forma comprensible | Sí | Mensajes con códigos; fallback `5xx` y `fetch` |
| Las reglas quedan en negocio y el acceso a datos en persistencia | Sí | `servicios/` y `persistencia/` |
| La autenticación por rol no altera rutas ni claves documentadas | Sí | `/auth/token`, `test_autenticacion.py` y `supabase_verificacion.txt` |
| PostgreSQL queda verificado con índices y triggers | Sí | `schema_postgres.sql` y `supabase_verificacion.txt` |
| La matriz conserva trazabilidad RF–RNF–prueba–evidencia | Sí | Sección 5 |
| Los resultados de calidad se comparan con las metas acordadas | Sí | Metas y medidas en la matriz |
| Se identifican incumplimientos, no verificados y limitaciones | Sí | Todos los RNF medidos; limitaciones de alcance en la sección 8 |
| Otra persona puede repetir la demostración con el README | Sí | Sección 6 y `README.md` |

---

## 8. Limitaciones y cierre

**Limitaciones actuales**

- Las fotos se registran por nombre de archivo; no se almacena el binario.
- La medición secuencial de RNF-05 y la medición concurrente son alcances distintos; no se comparan entre sí.
- En RNF-07 cada adoptante se representa con una consulta autenticada al catálogo; no se modela un flujo de adopción.
- El token vive en memoria: al recargar la página hay que iniciar sesión de nuevo.
- El hashing PBKDF2 y el JWT son la autenticación básica del corte; no se usa Supabase Auth.

**Cierre de la semana 3 del prototipo**

La autenticación por roles y la migración a PostgreSQL ya quedaron implementadas
y verificadas sin cambiar rutas ni claves JSON. La concurrencia de RNF-05 y la
prueba de RNF-07 están cerradas tanto en local como contra Supabase. Queda como
trabajo futuro el almacenamiento binario de imágenes y el rechazo automático de
solicitudes pendientes al dar de baja (RN-15), fuera del alcance del corte.
