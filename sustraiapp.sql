-- Scripts SQL para Esquemas
CREATE SCHEMA IF NOT EXISTS user_data;
CREATE SCHEMA IF NOT EXISTS market_data;

-- ==========================================
-- ESQUEMA: user_data
-- ==========================================

-- Tabla Users
CREATE TABLE IF NOT EXISTS user_data.users (
    id_user SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    tlf VARCHAR(20),
    municipio VARCHAR(100) NOT NULL,
    provincia VARCHAR(50) NOT NULL,
    sexo VARCHAR(10) NOT NULL CHECK (sexo IN ('hombre', 'mujer')),
    age INTEGER NOT NULL CHECK (age > 0 AND age < 120),
    role VARCHAR(10) NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Intereses (Jerárquica)
CREATE TABLE IF NOT EXISTS user_data.interests (
    id_interes SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL, -- Categoría padre, hijo o nieto
    father_id INTEGER REFERENCES user_data.interests(id_interes) ON DELETE SET NULL, -- NULL si es raíz
    level INTEGER NOT NULL DEFAULT 0 -- 0: Padre, 1: Hijo, 2: Nieto (opcional para facilitar lógica)
);

-- Tabla Relación Usuario-Intereses
CREATE TABLE IF NOT EXISTS user_data.user_interests (
    id_user INTEGER NOT NULL REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    id_interes INTEGER NOT NULL REFERENCES user_data.interests(id_interes) ON DELETE CASCADE,
    PRIMARY KEY (id_user, id_interes)
);

-- Tabla de Preferencias Generales del Usuario
CREATE TABLE IF NOT EXISTS user_data.preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    le_gusta_gastro BOOLEAN NOT NULL DEFAULT FALSE,
    le_gusta_cultura BOOLEAN NOT NULL DEFAULT FALSE,
    le_gusta_eventos BOOLEAN NOT NULL DEFAULT FALSE,
    le_gusta_compras BOOLEAN NOT NULL DEFAULT FALSE,
    rango_precio VARCHAR(10) CHECK (rango_precio IN ('bajo', 'medio', 'alto')),
    movilidad_reducida BOOLEAN DEFAULT FALSE,
    municipios_interes JSONB, -- Ej: ["Bilbao", "Getxo"]
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de Reseñas (Polimórfica)
CREATE TABLE IF NOT EXISTS user_data.reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES user_data.users(id_user) ON DELETE CASCADE,
    entidad_tipo VARCHAR(50) NOT NULL CHECK (entidad_tipo IN ('event', 'gastro', 'cultura', 'store')),
    entidad_id INTEGER NOT NULL, -- ID de la tabla correspondiente en market_data
    puntuacion INTEGER NOT NULL CHECK (puntuacion >= 1 AND puntuacion <= 5),
    texto TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_reviews_entity ON user_data.reviews (entidad_tipo, entidad_id);

-- ==========================================
-- ESQUEMA: market_data
-- ==========================================

-- Tabla Events
CREATE TABLE IF NOT EXISTS market_data.events (
    id SERIAL PRIMARY KEY,
    id_kulturklik VARCHAR(50) UNIQUE NOT NULL, -- ID externo único
    type VARCHAR(50), -- ID del tipo
    type_es VARCHAR(100), -- Tipo legible: Concierto, Teatro...
    nombre_es VARCHAR(255) NOT NULL,
    descripcion_es TEXT,
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    publication_date TIMESTAMP WITH TIME ZONE,
    language VARCHAR(10), -- EN/ES/EU
    opening_hours_es VARCHAR(100),
    source_name_es VARCHAR(100),
    source_url_es TEXT,
    price_es VARCHAR(100),
    purchase_url_es TEXT,
    municipality_es VARCHAR(100) NOT NULL,
    url_compra_es TEXT,
    municipality_latitude FLOAT,
    municipality_longitude FLOAT,
    municipality_nora_code VARCHAR(20),
    province_nora_code VARCHAR(20), -- 01, 48, 20
    establishment_es VARCHAR(255),
    url_event_es TEXT,
    url_name_es VARCHAR(100),
    images JSONB, -- Array de objetos imagen
    place_es VARCHAR(255),
    online BOOLEAN DEFAULT FALSE,
    url_online_es TEXT,
    company_es VARCHAR(255),
    subtipo VARCHAR(100),
    price_eur FLOAT,
    is_free BOOLEAN DEFAULT FALSE,
    year INTEGER,
    month INTEGER,
    weekday VARCHAR(20),
    is_weekend BOOLEAN DEFAULT FALSE,
    duration_days INTEGER,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_events_start_date ON market_data.events (start_date);
CREATE INDEX IF NOT EXISTS idx_events_municipality ON market_data.events (municipality_es);
CREATE INDEX IF NOT EXISTS idx_events_active ON market_data.events (active);

-- Tabla Gastronomy
CREATE TABLE IF NOT EXISTS market_data.gastronomy (
    id SERIAL PRIMARY KEY,
    google_place_id VARCHAR(100) UNIQUE NOT NULL, -- ID único de Google Places
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    municipio VARCHAR(100),
    provincia VARCHAR(50),
    latitud FLOAT, -- Coordenadas como FLOAT
    longitud VARCHAR(50), -- Según especificación (aunque recomiendo FLOAT para consistencia)
    type VARCHAR(50), -- Ej: Restauración
    tipo_comida VARCHAR(100), -- Ej: Asador, Sidrería
    entorno VARCHAR(100), -- Ej: Costa Vasca
    email VARCHAR(100),
    web TEXT,
    web_euskadi TEXT,
    categoria VARCHAR(50), -- Ej: restaurantes, bodegas
    calidad BOOLEAN DEFAULT FALSE,
    url_imagen TEXT,
    valoracion FLOAT, -- Puntuación media Google (1-5)
    num_resenas INTEGER,
    nivel_precio VARCHAR(50), -- Ej: PRICE_LEVEL_MODERATE
    national_phone_number VARCHAR(20), -- Teléfono de contacto
    active BOOLEAN DEFAULT TRUE, -- Por defecto activo
    michelin BOOLEAN DEFAULT FALSE, -- Estrella Michelin
    repsol BOOLEAN DEFAULT FALSE, -- Sol Repsol
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsquedas rápidas por municipio y estado activo
CREATE INDEX IF NOT EXISTS idx_gastro_municipality_active ON market_data.gastronomy (municipio, active);

-- Tabla Culture
CREATE TABLE IF NOT EXISTS market_data.culture (
    id SERIAL PRIMARY KEY,
    google_place_id VARCHAR(100) UNIQUE, -- Único si presente
    kulturklik_id VARCHAR(50) UNIQUE, -- Único si presente
    fuente VARCHAR(50) NOT NULL DEFAULT 'Open Data',
    nombre VARCHAR(255) NOT NULL,
    tipo_lugar VARCHAR(100) NOT NULL, -- museo, teatro...
    tipo_cultura VARCHAR(100),
    descripcion TEXT,
    precio VARCHAR(100),
    horario JSONB,
    telefono VARCHAR(50),
    email VARCHAR(100),
    web VARCHAR(255),
    web_amigable VARCHAR(255),
    imagen_url TEXT,
    municipio VARCHAR(100) NOT NULL,
    provincia VARCHAR(50) NOT NULL,
    direccion VARCHAR(255),
    codigo_postal VARCHAR(20), -- Corregido a VARCHAR, los CP no son floats
    visita_guiada BOOLEAN DEFAULT FALSE,
    capacidad INTEGER,
    tienda BOOLEAN DEFAULT FALSE,
    lat FLOAT NOT NULL,
    lng FLOAT NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valoracion FLOAT,
    numero_valoraciones INTEGER
);

CREATE INDEX IF NOT EXISTS idx_culture_municipality ON market_data.culture (municipio);
CREATE INDEX IF NOT EXISTS idx_culture_active ON market_data.culture (active);