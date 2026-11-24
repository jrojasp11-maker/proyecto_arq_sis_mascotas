# Contratos de la API — RF-05, RF-34 y autenticación

Base local: `http://127.0.0.1:8000/api/v1`
Documentación interactiva: `http://127.0.0.1:8000/docs`
Especificación OpenAPI: `http://127.0.0.1:8000/openapi.json`

Formato: JSON, nombres en `snake_case`, identificadores enteros y fechas
`AAAA-MM-DD`. Todos los errores usan la misma estructura:

```json
{
  "detail": "mensaje legible",
  "codigo": "ERR-004"
}
```

## Autenticación y roles

Las operaciones de escritura de `/api/v1` requieren la cabecera
`Authorization: Bearer <access_token>`, obtenida en el único endpoint nuevo:

`POST /auth/token` (sin autenticación previa). La consulta `GET /mascotas` es pública.

Cuerpo:

```json
{
  "usuario": "refugio",
  "contrasena": "<credencial-demo>"
}
```

Respuesta `200 OK`:

```json
{
  "access_token": "<jwt-hs256-firmado>",
  "token_type": "bearer",
  "rol": "refugio",
  "refugio_id": 1,
  "expires_in": 3600
}
```

Los roles son `refugio`, `adoptante` y `admin`. Las contraseñas se verifican con
PBKDF2-HMAC-SHA256 y el token se firma con JWT HS256 mediante
`AUTH_JWT_SECRET`. La interfaz solicita las credenciales en `/ui/`, guarda el
token solo en memoria y lo envía en las operaciones de escritura.

| Rol | `GET /mascotas` | `POST`, `PUT` y `DELETE /mascotas` |
|---|---|---|
| `adoptante` | Público | Denegado (`403` ERR-403) |
| `refugio` | Público | Solo sobre su `refugio_id` |
| `admin` | Público | Cualquier refugio |

En las escrituras, si falta el token, no es válido o expiró, la respuesta es `401` con ERR-401.
Si el token es válido pero el rol no puede ejecutar la operación, la respuesta
es `403` con ERR-403. Un `refugio` que intente actuar por otro refugio recibe
`403` ERR-003.

**Invariantes.** No se cambiaron rutas ni claves JSON ya documentadas. El campo
`refugio_id` se conserva en POST/PUT/DELETE por compatibilidad y se compara con
el usuario autenticado; el `admin` está exento de esa comparación. Las claves de
éxito, los códigos ERR-004, ERR-006, ERR-008, ERR-009 y ERR-011, las reglas de
negocio y los formatos de fecha permanecen iguales.

## Resumen de endpoints

| RF | Método y ruta | Servicio invocado | Éxito | Errores posibles |
|---|---|---|---|---|
| Autenticación | `POST /auth/token` | `seguridad.autenticacion` | `200` JWT y rol | `401` ERR-401 |
| RF-05 | `POST /mascotas` | `ServicioMascotas.crear` | `201` ficha creada | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-008, `409` ERR-009 |
| RF-05 | `PUT /mascotas/{id}` | `ServicioMascotas.actualizar` | `200` ficha actualizada | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-011 |
| RF-05 | `DELETE /mascotas/{id}?refugio_id={id}` | `ServicioMascotas.dar_de_baja` | `204` sin cuerpo | `400` ERR-004, `401` ERR-401, `403` ERR-003/ERR-403, `404` ERR-011 |
| RF-34 | `GET /mascotas` | `ServicioCatalogo.listar` | `200` página del catálogo | `400` ERR-004 |

## Códigos de error

| Código | HTTP | Significado |
|---|---|---|
| `ERR-003` | `403` | La ficha no pertenece al refugio indicado |
| `ERR-004` | `400` | Datos de entrada inválidos (tipo, dominio, rango, formato) |
| `ERR-006` | `409` | Violación de integridad de la base |
| `ERR-008` | `404` | El refugio no existe |
| `ERR-009` | `409` | El refugio no está verificado y no puede publicar |
| `ERR-011` | `404` | La ficha no existe |
| `ERR-401` | `401` | Token o credenciales ausentes, inválidos o expirados |
| `ERR-403` | `403` | El rol autenticado no puede ejecutar la operación |

Un error inesperado responde `500` con `{"detail": "Error interno del servidor.", "codigo": "ERR-500"}`
y se registra en el servidor sin exponer detalles técnicos. Las validaciones de
forma y tipo también responden `400` con `ERR-004` (no `422`), para mantener un
único contrato de error.

---

## RF-05 · Crear ficha

`POST /mascotas`

Requiere token de `refugio` o `admin`. Cuerpo:

```json
{
  "refugio_id": 1,
  "nombre": "Nala",
  "raza": "Mestiza",
  "especie": "perro",
  "edad_meses": 24,
  "tamano": "mediano",
  "nivel_energia": "media",
  "experiencia_requerida": "basica",
  "apta_con_menores": true,
  "apta_con_mascotas": true,
  "historial_salud": "Vacunas al día",
  "historial_comportamiento": "Sociable",
  "fecha_publicacion": "2026-11-10",
  "fotografias": ["nala_01.jpg", "nala_02.jpg"]
}
```

Respuesta `201 Created` (el `id` depende de la base; en la base de prueba es `7`):

```json
{
  "id": 7,
  "refugio_id": 1,
  "nombre": "Nala",
  "raza": "Mestiza",
  "especie": "perro",
  "edad_meses": 24,
  "tamano": "mediano",
  "nivel_energia": "media",
  "experiencia_requerida": "basica",
  "apta_con_menores": true,
  "apta_con_mascotas": true,
  "historial_salud": "Vacunas al día",
  "historial_comportamiento": "Sociable",
  "estado": "disponible",
  "fecha_publicacion": "2026-11-10",
  "creado_en": "2026-11-10 13:46:00",
  "refugio_nombre": "Refugio Patitas",
  "refugio_localidad": "ENGATIVA",
  "refugio_estado": "verificado",
  "fotografias": [
    {"id": 7, "archivo": "nala_01.jpg", "orden": 1},
    {"id": 8, "archivo": "nala_02.jpg", "orden": 2}
  ]
}
```

Reglas aplicadas: `refugio_id` debe existir (`404` ERR-008) y estar verificado
(`409` ERR-009). El estado inicial lo define el backend: `disponible` si hay
entre 1 y 5 fotos JPG/PNG; `incompleta` si no hay fotos. Una ficha incompleta no
aparece en el catálogo. El `refugio_id` del cuerpo debe coincidir con el token
salvo que el actor sea `admin`.

Rechazo de refugio no verificado (`409 Conflict`):

```json
{
  "detail": "el refugio 2 no está verificado y no puede publicar fichas",
  "codigo": "ERR-009"
}
```

---

## RF-05 · Actualizar ficha

`PUT /mascotas/{id}`

Requiere token de `refugio` o `admin`. Todos los campos son opcionales, excepto
`refugio_id` (actor). Si se envía `fotografias`, reemplaza la lista completa y
recalcula el estado.

```json
{
  "refugio_id": 1,
  "nombre": "Nala actualizada",
  "fotografias": ["nala_01.jpg"]
}
```

Respuesta `200 OK`: ficha completa con `estado` y `fotografias` actualizados.
Errores: `400` ERR-004 (campo inválido o sin cambios), `403` ERR-003 (la ficha
pertenece a otro refugio), `404` ERR-011 (la ficha no existe), `403` ERR-403 si
el rol no puede editar.

---

## RF-05 · Dar de baja ficha

`DELETE /mascotas/{id}?refugio_id={id}`

Sin cuerpo. Requiere token de `refugio` o `admin`. Respuesta `204 No Content`.
La baja es lógica: la ficha pasa a `baja` y deja de aparecer en el catálogo
(RN-15). Errores: `403` ERR-003, `404` ERR-011, `400` ERR-004 si falta
`refugio_id`, y `403` ERR-403 si el rol no puede dar de baja.

---

## RF-34 · Consultar catálogo

`GET /mascotas`

No requiere autenticación. Parámetros opcionales:

| Parámetro | Tipo | Regla |
|---|---|---|
| `especie` | texto | `perro` o `gato` |
| `tamano` | texto | `pequeno`, `mediano` o `grande` |
| `edad_min` | entero | `>= 0` |
| `edad_max` | entero | `>= 0` y `>= edad_min` |
| `pagina` | entero | `>= 1`, por defecto `1` |
| `por_pagina` | entero | entre `1` y `100`, por defecto `20` |

Respuesta `200 OK` (catálogo inicial de la base de prueba):

```json
{
  "total": 3,
  "pagina": 1,
  "por_pagina": 20,
  "mascotas": [
    {
      "id": 1,
      "nombre": "Luna",
      "especie": "perro",
      "edad_meses": 30,
      "tamano": "grande",
      "nivel_energia": "alta",
      "fecha_publicacion": "2026-10-01",
      "refugio_id": 1,
      "refugio_nombre": "Refugio Patitas",
      "refugio_localidad": "ENGATIVA",
      "foto_principal": "luna_01.jpg"
    }
  ]
}
```

El ejemplo muestra solo la primera fila; la respuesta real incluye las tres
fichas en orden `Luna (1), Rocky (3), Milo (2)`.

Reglas: solo fichas `disponible` de refugios `verificado`, ordenadas por
`fecha_publicacion` ascendente y, a igual fecha, por `id` ascendente. No se
exponen datos personales (RNF-04).

Condición límite (filtro válido sin coincidencias) — `200 OK`:

```json
{
  "total": 0,
  "pagina": 1,
  "por_pagina": 20,
  "mascotas": []
}
```

Filtro inválido — `400 Bad Request`:

```json
{
  "detail": "especie debe ser perro o gato",
  "codigo": "ERR-004"
}
```

---

## Cierre e integración

- Origen local permitido por CORS: `http://localhost:5173` y
  `http://127.0.0.1:5173` (configurable con `CORS_ORIGINS`).
- La interfaz en `/ui/` exige inicio de sesión para abrir el corte; la consulta
  API del catálogo es pública y las escrituras usan el JWT de `/auth/token`.
- Persistencia: PostgreSQL en Supabase, esquema `aqsis`, cuando existe
  `DATABASE_URL`; si no, SQLite local con `DB_PATH`.
- URL pública de la demostración: <https://aqsis-corte-vertical.vercel.app/ui/>.
- Si el cliente pierde la respuesta de un POST, debe consultar el catálogo antes
  de repetir la escritura para no duplicar fichas.
- Evidencias: `evidencias/supabase_verificacion.txt` y
  `evidencias/rnf_supabase.txt` registran roles, RF, índices, triggers y RNF
  sobre la base remota.
