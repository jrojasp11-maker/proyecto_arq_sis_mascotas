-- Carga inicial de aqsis en PostgreSQL. Estado idéntico a seed.sql (semana 13).
-- El catálogo debe devolver 3 fichas: Luna (1), Rocky (3) y Milo (2).

INSERT INTO aqsis.refugio (id, nombre, localidad, estado_verificacion) VALUES
    (1, 'Refugio Patitas',   'ENGATIVA', 'verificado'),
    (2, 'Fundación Colitas', 'SUBA',     'pendiente');

INSERT INTO aqsis.mascota
    (id, refugio_id, nombre, raza, especie, edad_meses, tamano, nivel_energia,
     experiencia_requerida, apta_con_menores, apta_con_mascotas,
     historial_salud, historial_comportamiento, estado, fecha_publicacion)
VALUES
    (1, 1, 'Luna',  'Mestiza', 'perro', 30, 'grande',  'alta',  'basica',  1, 1,
     'Vacunas al día', 'Sociable', 'disponible', '2026-10-01'),
    (2, 1, 'Milo',  'Criollo', 'gato',  18, 'pequeno', 'media', 'ninguna', 1, 1,
     'Sin novedades', 'Tranquilo', 'disponible', '2026-10-05'),
    (3, 1, 'Rocky', 'Mestizo', 'perro', 60, 'mediano', 'alta',  'amplia',  0, 0,
     'Control cardíaco', 'Requiere manejo experimentado', 'disponible', '2026-10-03'),
    (4, 2, 'Nube',  'Criollo', 'gato',   8, 'pequeno', 'baja',  'ninguna', 1, 1,
     NULL, NULL, 'disponible', '2026-10-02'),
    (5, 1, 'Toby',  'Mestizo', 'perro', 12, 'pequeno', 'media', 'ninguna', 1, 1,
     NULL, NULL, 'incompleta', '2026-10-04'),
    (6, 1, 'Canela','Mestiza', 'perro', 48, 'mediano', 'media', 'basica',  1, 1,
     NULL, NULL, 'adoptada', '2026-09-20');

INSERT INTO aqsis.fotografia (mascota_id, archivo, orden) VALUES
    (1, 'luna_01.jpg',   1),
    (1, 'luna_02.jpg',   2),
    (2, 'milo_01.jpg',   1),
    (3, 'rocky_01.jpg',  1),
    (4, 'nube_01.jpg',   1),
    (6, 'canela_01.jpg', 1);

-- Usuarios demo. El hash se sobrescribe desde migrar_supabase.py para no fijar
-- una sal en el repositorio; aquí solo se deja un marcador válido.
INSERT INTO aqsis.usuario (nombre_usuario, contrasena_hash, rol, refugio_id) VALUES
    ('refugio',   'pendiente', 'refugio',   1),
    ('adoptante', 'pendiente', 'adoptante', NULL),
    ('admin',     'pendiente', 'admin',     NULL);

SELECT setval(pg_get_serial_sequence('aqsis.refugio', 'id'),
              (SELECT MAX(id) FROM aqsis.refugio), true);
SELECT setval(pg_get_serial_sequence('aqsis.mascota', 'id'),
              (SELECT MAX(id) FROM aqsis.mascota), true);
SELECT setval(pg_get_serial_sequence('aqsis.fotografia', 'id'),
              (SELECT MAX(id) FROM aqsis.fotografia), true);
SELECT setval(pg_get_serial_sequence('aqsis.usuario', 'id'),
              (SELECT MAX(id) FROM aqsis.usuario), true);
