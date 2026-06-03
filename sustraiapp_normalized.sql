-- =============================================================
-- SUSTRAIAPP — Esquema v4 (Simplificado + Cualificaciones)
-- =============================================================

CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS user_data;


-- =============================================================
-- ESQUEMA: shared
-- =============================================================

CREATE TABLE IF NOT EXISTS shared.municipalities (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    provincia       VARCHAR(50)  NOT NULL,
    nora_code       VARCHAR(20)  UNIQUE,
    province_code   VARCHAR(5),
    lat             FLOAT,
    lng             FLOAT,
    UNIQUE (nombre, provincia)
);


-- =============================================================
-- ESQUEMA: market_data
-- =============================================================

CREATE TABLE IF NOT EXISTS market_data.events (
    id                  SERIAL PRIMARY KEY,
    external_id         VARCHAR(100) UNIQUE, -- Opcional: para ID externo si hace falta
    municipality_id     INTEGER      NOT NULL REFERENCES shared.municipalities(id) ON DELETE RESTRICT,
    type                VARCHAR(50),
    subtipo             VARCHAR(100),
    start_date          TIMESTAMPTZ  NOT NULL,
    end_date            TIMESTAMPTZ  NOT NULL,
    publication_date    TIMESTAMPTZ,
    language            VARCHAR(10),
    opening_hours       VARCHAR(100),
    price_eur           FLOAT,
    is_free             BOOLEAN DEFAULT FALSE,
    is_sponsored        BOOLEAN DEFAULT FALSE,
    purchase_url        TEXT,
    url_event           TEXT,
    url_online          TEXT,
    images              JSONB,
    online              BOOLEAN DEFAULT FALSE,
    establishment       VARCHAR(255),
    place               VARCHAR(255),
    company             VARCHAR(255),
    active              BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_start_date   ON market_data.events (start_date);
CREATE INDEX IF NOT EXISTS idx_events_municipality ON market_data.events (municipality_id);
CREATE INDEX IF NOT EXISTS idx_events_active       ON market_data.events (active);

-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS market_data.gastronomy (
    id                      SERIAL PRIMARY KEY,
    external_id             VARCHAR(100) UNIQUE, -- Opcional
    nombre                  VARCHAR(255) NOT NULL,
    descripcion             TEXT,
    municipality_id         INTEGER NOT NULL REFERENCES shared.municipalities(id) ON DELETE RESTRICT,
    lat                     FLOAT,
    lng                     FLOAT,
    type                    VARCHAR(50),
    tipo_comida             VARCHAR(100),
    entorno                 VARCHAR(100),
    email                   VARCHAR(100),
    web                     TEXT,
    web_euskadi             TEXT,
    categoria               VARCHAR(50),
    calidad                 BOOLEAN DEFAULT FALSE,
    url_imagen              TEXT,
    valoracion              FLOAT CHECK (valoracion >= 1 AND valoracion <= 5),
    num_resenas             INTEGER,
    nivel_precio            VARCHAR(50),
    national_phone_number   VARCHAR(20),
    -- Eliminados michelin y repsol -> ahora van en gastronomy_qualifications
    is_sponsored            BOOLEAN DEFAULT FALSE,
    active                  BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gastro_municipality_active
    ON market_data.gastronomy (municipality_id, active);

-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS market_data.culture (
    id                  SERIAL PRIMARY KEY,
    external_id         VARCHAR(100) UNIQUE, -- Opcional
    fuente              VARCHAR(50)  NOT NULL DEFAULT 'Manual'
                            CHECK (fuente IN ('Google Places', 'Kulturklik', 'Open Data', 'Manual')),
    nombre              VARCHAR(255) NOT NULL,
    tipo_lugar          VARCHAR(100) NOT NULL,
    tipo_cultura        VARCHAR(100),
    descripcion         TEXT,
    precio              VARCHAR(100),
    horario             JSONB,
    telefono            VARCHAR(50),
    email               VARCHAR(100),
    web                 VARCHAR(255),
    web_amigable        VARCHAR(255),
    imagen_url          TEXT,
    municipality_id     INTEGER NOT NULL REFERENCES shared.municipalities(id) ON DELETE RESTRICT,
    direccion           VARCHAR(255),
    codigo_postal       VARCHAR(10),
    visita_guiada       BOOLEAN DEFAULT FALSE,
    capacidad           INTEGER,
    tienda              BOOLEAN DEFAULT FALSE,
    lat                 FLOAT   NOT NULL,
    lng                 FLOAT   NOT NULL,
    valoracion          FLOAT CHECK (valoracion >= 1 AND valoracion <= 5),
    numero_valoraciones INTEGER,
    is_sponsored        BOOLEAN DEFAULT FALSE,
    active              BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_culture_municipality ON market_data.culture (municipality_id);
CREATE INDEX IF NOT EXISTS idx_culture_active       ON market_data.culture (active);
CREATE INDEX IF NOT EXISTS idx_culture_tipo_lugar   ON market_data.culture (tipo_lugar);

-- -------------------------------------------------------------------
-- Cualificaciones (Simplificado)
-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS market_data.qualifications (
    id          SERIAL PRIMARY KEY,
    codigo      VARCHAR(50)  UNIQUE, -- Opcional, útil para filtros internos
    nombre      VARCHAR(100) NOT NULL
);

-- Catálogo inicial
INSERT INTO market_data.qualifications (codigo, nombre) VALUES
    ('repsol_sol',          'Sol Repsol'),
    ('michelin_estrella',   'Estrella Michelin'),
    ('denominacion_origen', 'Denominación de Origen'),
    ('q_calidad',           'Q de Calidad Turística'),
    ('euskolabel',          'Eusko Label'),
    ('agricultura_eco',     'Agricultura Ecológica'),
    ('euskal_baserri',      'Euskal Baserri')
ON CONFLICT (codigo) DO NOTHING;

-- Tabla de relación (Simplificada: sin fechas ni notas)
CREATE TABLE IF NOT EXISTS market_data.gastronomy_qualifications (
    id                  SERIAL PRIMARY KEY,
    gastronomy_id       INTEGER NOT NULL REFERENCES market_data.gastronomy(id)      ON DELETE CASCADE,
    qualification_id    INTEGER NOT NULL REFERENCES market_data.qualifications(id)  ON DELETE RESTRICT,
    UNIQUE (gastronomy_id, qualification_id)
);

CREATE INDEX IF NOT EXISTS idx_gastro_qualif_gastronomy
    ON market_data.gastronomy_qualifications (gastronomy_id);
CREATE INDEX IF NOT EXISTS idx_gastro_qualif_qualification
    ON market_data.gastronomy_qualifications (qualification_id);

-- Vista actualizada
CREATE OR REPLACE VIEW market_data.gastronomy_with_qualifications AS
SELECT
    g.id,
    g.nombre,
    g.municipality_id,
    g.valoracion,
    g.active,
    COALESCE(
        JSON_AGG(
            JSON_BUILD_OBJECT(
                'id',     q.id,
                'nombre', q.nombre
            )
        ) FILTER (WHERE q.id IS NOT NULL),
        '[]'
    ) AS cualificaciones
FROM market_data.gastronomy g
LEFT JOIN market_data.gastronomy_qualifications gq ON gq.gastronomy_id = g.id
LEFT JOIN market_data.qualifications            q  ON q.id = gq.qualification_id
GROUP BY g.id;


-- =============================================================
-- ESQUEMA: user_data
-- =============================================================

CREATE TABLE IF NOT EXISTS user_data.users (
    id_user         SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    apellido        VARCHAR(100),
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(256) NOT NULL,
    tlf             VARCHAR(20),
    municipality_id INTEGER      NOT NULL REFERENCES shared.municipalities(id) ON DELETE RESTRICT,
    sexo            VARCHAR(10)  NOT NULL CHECK (sexo IN ('hombre', 'mujer', 'otro')),
    age             INTEGER      NOT NULL CHECK (age > 0 AND age < 120),
    role            VARCHAR(10)  NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_data.interests (
    id_interes  SERIAL  PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    father_id   INTEGER REFERENCES user_data.interests(id_interes) ON DELETE SET NULL,
    level       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_data.user_interests (
    id_user     INTEGER NOT NULL REFERENCES user_data.users(id_user)        ON DELETE CASCADE,
    id_interes  INTEGER NOT NULL REFERENCES user_data.interests(id_interes) ON DELETE CASCADE,
    PRIMARY KEY (id_user, id_interes)
);

-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_data.preferences (
    id                  SERIAL  PRIMARY KEY,
    user_id             INTEGER NOT NULL UNIQUE REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    rango_precio        VARCHAR(10)  CHECK (rango_precio IN ('bajo', 'medio', 'alto')),
    movilidad_reducida  BOOLEAN DEFAULT FALSE,
    municipios_interes  INTEGER[]    DEFAULT '{}',
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- -------------------------------------------------------------------
-- Reviews (Mantenemos estructura separada o única según prefieras, 
-- aquí dejo la versión única con CHECK constraint como en v2/v3)
-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_data.reviews (
    id          SERIAL  PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES user_data.users(id_user)   ON DELETE CASCADE,
    event_id    INTEGER          REFERENCES market_data.events(id)     ON DELETE CASCADE,
    gastro_id   INTEGER          REFERENCES market_data.gastronomy(id) ON DELETE CASCADE,
    culture_id  INTEGER          REFERENCES market_data.culture(id)    ON DELETE CASCADE,
    puntuacion  INTEGER NOT NULL CHECK (puntuacion >= 1 AND puntuacion <= 5),
    texto       TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT reviews_single_entity CHECK (
        (event_id   IS NOT NULL)::int +
        (gastro_id  IS NOT NULL)::int +
        (culture_id IS NOT NULL)::int = 1
    )
);

CREATE INDEX IF NOT EXISTS idx_reviews_event   ON user_data.reviews (event_id)   WHERE event_id   IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_gastro  ON user_data.reviews (gastro_id)  WHERE gastro_id  IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reviews_culture ON user_data.reviews (culture_id) WHERE culture_id IS NOT NULL;

-- -------------------------------------------------------------------
-- Favoritos
-- -------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS user_data.favorites (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER     NOT NULL REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    entidad_id      INTEGER     NOT NULL,
    entidad_tipo    VARCHAR(20) NOT NULL CHECK (entidad_tipo IN ('evento', 'gastronomia', 'cultura')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, entidad_id, entidad_tipo)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user ON user_data.favorites (user_id);


-- =============================================================
-- SEED DATA (Municipios e Intereses básicos)
-- =============================================================

INSERT INTO shared.municipalities (nombre, provincia, nora_code, province_code, lat, lng) VALUES
    ('Bilbao',          'Bizkaia',   NULL, '48',  43.2630, -2.9350),
    ('Getxo',           'Bizkaia',   NULL, '48',  43.3563, -3.0097),
    ('Barakaldo',       'Bizkaia',   NULL, '48',  43.2963, -2.9942),
    ('San Sebastián',   'Gipuzkoa',  NULL, '20',  43.3183, -1.9812),
    ('Vitoria-Gasteiz', 'Álava',     NULL, '01',  42.8469, -2.6728),
    ('Irún',            'Gipuzkoa',  NULL, '20',  43.3390, -1.7886),
    ('Ermua',           'Bizkaia',   NULL, '48',  43.1897, -2.5011),
    ('Durango',         'Bizkaia',   NULL, '48',  43.1706, -2.6325)
ON CONFLICT (nombre, provincia) DO NOTHING;

-- Raíces Intereses
INSERT INTO user_data.interests (nombre, father_id, level) VALUES
    ('Eventos',            NULL, 0),
    ('Gastronomía',        NULL, 0),
    ('Puntos de Interés',  NULL, 0)
ON CONFLICT DO NOTHING;

-- Eventos Level 1
INSERT INTO user_data.interests (nombre, father_id, level)
SELECT nombre, (SELECT id_interes FROM user_data.interests WHERE nombre = 'Eventos' AND level = 0), 1
FROM (VALUES
    ('Concierto'), ('Festival'), ('Fiestas'), ('Feria'), ('Teatro'),
    ('Danza'), ('Conferencia'), ('Cine'), ('Exposición')
) AS t(nombre) ON CONFLICT DO NOTHING;

-- Gastronomía Level 1
INSERT INTO user_data.interests (nombre, father_id, level)
SELECT nombre, (SELECT id_interes FROM user_data.interests WHERE nombre = 'Gastronomía' AND level = 0), 1
FROM (VALUES
    ('Restaurantes'), ('Bodegas'), ('Gourmet')
) AS t(nombre) ON CONFLICT DO NOTHING;

-- Puntos de Interés Level 1
INSERT INTO user_data.interests (nombre, father_id, level)
SELECT nombre, (SELECT id_interes FROM user_data.interests WHERE nombre = 'Puntos de Interés' AND level = 0), 1
FROM (VALUES ('Museos'), ('Patrimonio Cultural')) AS t(nombre)
ON CONFLICT DO NOTHING;