-- =============================================================
-- SUSTRAIAPP — Esquema normalizado (v2)
-- =============================================================
-- Cambios respecto a v1:
--   1. Tabla shared.municipalities  → elimina geografía desnormalizada
--   2. Tabla shared.translations    → i18n sin sufijos _es/_eu/_en
--   3. reviews con FKs explícitas   → sustituye FK polimórfica rota
--   4. Preferencias via interests   → elimina booleans redundantes
--   5. Coordenadas unificadas FLOAT → corrige VARCHAR en gastronomy
--   6. Eliminadas columnas calculadas en events → calcular en consulta con AT TIME ZONE
--   7. culture: fuentes separadas   → google_place_id / kulturklik_id sin ambigüedad
-- Orden de creación: shared → market_data → user_data (respeta dependencias FK)
-- =============================================================

CREATE SCHEMA IF NOT EXISTS shared;
CREATE SCHEMA IF NOT EXISTS market_data;
CREATE SCHEMA IF NOT EXISTS user_data;


-- =============================================================
-- ESQUEMA: shared  (datos de referencia compartidos)
-- =============================================================

-- Municipios normalizados — única fuente de verdad geográfica
-- Referenciado por users, gastronomy, culture, events y preferences
CREATE TABLE IF NOT EXISTS shared.municipalities (
    id              SERIAL PRIMARY KEY,
    nombre          VARCHAR(100) NOT NULL,
    provincia       VARCHAR(50)  NOT NULL,
    nora_code       VARCHAR(20)  UNIQUE,
    province_code   VARCHAR(5),                    -- 01 Álava / 48 Bizkaia / 20 Gipuzkoa
    lat             FLOAT,
    lng             FLOAT,
    UNIQUE (nombre, provincia)
);

-- Traducciones genéricas — elimina los sufijos _es/_eu/_en de todas las tablas
-- entidad_tipo: 'event' | 'gastronomy' | 'culture'
CREATE TABLE IF NOT EXISTS shared.translations (
    id              SERIAL PRIMARY KEY,
    entidad_tipo    VARCHAR(50)  NOT NULL,
    entidad_id      INTEGER      NOT NULL,
    lang            VARCHAR(5)   NOT NULL,          -- 'es' | 'eu' | 'en'
    campo           VARCHAR(100) NOT NULL,          -- 'nombre' | 'descripcion' | 'source_name' …
    valor           TEXT         NOT NULL,
    UNIQUE (entidad_tipo, entidad_id, lang, campo)
);

CREATE INDEX IF NOT EXISTS idx_translations_entity
    ON shared.translations (entidad_tipo, entidad_id, lang);


-- =============================================================
-- ESQUEMA: market_data
-- =============================================================

-- Eventos
-- ELIMINADOS: municipality_es/latitude/longitude/province_nora_code → municipality_id FK
-- ELIMINADOS: nombre_es/descripcion_es/source_name_es/… → shared.translations
-- ELIMINADOS: year/month/weekday/is_weekend/duration_days → calcular en consulta
CREATE TABLE IF NOT EXISTS market_data.events (
    id                  SERIAL  PRIMARY KEY,
    id_kulturklik       VARCHAR(50)  UNIQUE NOT NULL,
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

-- Gastronomía
-- CORREGIDO: longitud era VARCHAR(50) → ahora FLOAT
-- ELIMINADOS: municipio/provincia inline → municipality_id FK
CREATE TABLE IF NOT EXISTS market_data.gastronomy (
    id                      SERIAL PRIMARY KEY,
    google_place_id         VARCHAR(100) UNIQUE NOT NULL,
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
    michelin                BOOLEAN DEFAULT FALSE,
    repsol                  BOOLEAN DEFAULT FALSE,
    active                  BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gastro_municipality_active
    ON market_data.gastronomy (municipality_id, active);

-- Cultura
-- SEPARADAS las dos fuentes (Google Places y Kulturklik) en columnas claramente opcionales
-- ELIMINADOS: municipio/provincia inline → municipality_id FK
CREATE TABLE IF NOT EXISTS market_data.culture (
    id                  SERIAL PRIMARY KEY,
    -- Una de las dos debe estar presente (ver CHECK)
    google_place_id     VARCHAR(100) UNIQUE,
    kulturklik_id       VARCHAR(50)  UNIQUE,
    fuente              VARCHAR(50)  NOT NULL DEFAULT 'Open Data'
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
    active              BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Al menos un identificador externo debe estar presente
    CONSTRAINT culture_requires_external_id CHECK (
        google_place_id IS NOT NULL OR kulturklik_id IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_culture_municipality ON market_data.culture (municipality_id);
CREATE INDEX IF NOT EXISTS idx_culture_active       ON market_data.culture (active);
CREATE INDEX IF NOT EXISTS idx_culture_tipo_lugar   ON market_data.culture (tipo_lugar);


-- =============================================================
-- ESQUEMA: user_data  (después de market_data por las FKs de reviews)
-- =============================================================

-- Usuarios
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

-- Árbol de intereses
CREATE TABLE IF NOT EXISTS user_data.interests (
    id_interes  SERIAL  PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL,
    father_id   INTEGER REFERENCES user_data.interests(id_interes) ON DELETE SET NULL,
    level       INTEGER NOT NULL DEFAULT 0          -- 0: raíz · 1: hijo · 2: nieto
);

-- Relación usuario ↔ intereses
CREATE TABLE IF NOT EXISTS user_data.user_interests (
    id_user     INTEGER NOT NULL REFERENCES user_data.users(id_user)        ON DELETE CASCADE,
    id_interes  INTEGER NOT NULL REFERENCES user_data.interests(id_interes) ON DELETE CASCADE,
    PRIMARY KEY (id_user, id_interes)
);

-- Preferencias del usuario
-- ELIMINADOS: le_gusta_gastro/cultura/eventos/compras → usar user_interests
-- ELIMINADOS: municipio/provincia inline → referencia a municipalities
CREATE TABLE IF NOT EXISTS user_data.preferences (
    id                  SERIAL  PRIMARY KEY,
    user_id             INTEGER NOT NULL UNIQUE REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    rango_precio        VARCHAR(10)  CHECK (rango_precio IN ('bajo', 'medio', 'alto')),
    movilidad_reducida  BOOLEAN DEFAULT FALSE,
    -- Array de IDs de municipios de interés (FK lógica hacia shared.municipalities)
    municipios_interes  INTEGER[]    DEFAULT '{}',
    updated_at          TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- Reseñas con FKs explícitas — sustituye la FK polimórfica sin constraint
-- Exactamente una de las tres FKs debe ser NOT NULL (ver CHECK al final)
-- Va al final porque referencia las tres tablas de market_data
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


-- =============================================================
-- DATOS DE REFERENCIA — Municipios del País Vasco
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