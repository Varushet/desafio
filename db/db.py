import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# 1. Cargar variables del archivo .env
load_dotenv()

# 2. Configuración de conexión
conn_params = {
    "dbname": os.getenv('DB_NAME', 'mi_proyecto_db'),
    "user": os.getenv('DB_USER', 'postgres'),
    "password": os.getenv('DB_PASSWORD'),
    "host": os.getenv('DB_HOST', 'localhost')
}

if not conn_params["password"]:
    raise ValueError("Error: Falta DB_PASSWORD en .env")

# 3. Obtener contraseña del admin desde .env
admin_pass = os.getenv('ADMIN_DEFAULT_PASSWORD')
if not admin_pass:
    raise ValueError("Error: Falta ADMIN_DEFAULT_PASSWORD en .env")

admin_hash = generate_password_hash(admin_pass)

# SQL a ejecutar
sql_script = f"""
CREATE SCHEMA IF NOT EXISTS user_data;
CREATE SCHEMA IF NOT EXISTS market_data;

CREATE TABLE IF NOT EXISTS user_data.users (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    apellido VARCHAR(50) NOT NULL,
    correo VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(256),
    tlf VARCHAR(20),
    municipio VARCHAR(100) NOT NULL,
    nivel VARCHAR(10) NOT NULL CHECK (nivel IN ('user', 'admin')),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO user_data.users (nombre, apellido, correo, password_hash, tlf, municipio, nivel)
VALUES ('Admin', 'Sistema', 'admin@proyecto.com', '{admin_hash}', NULL, 'Madrid', 'admin')
ON CONFLICT (correo) DO UPDATE SET 
    password_hash = EXCLUDED.password_hash,
    nivel = 'admin';
"""

try:
    conn = psycopg2.connect(**conn_params)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute(sql_script)
    
    print("✅ Base de datos inicializada. Admin configurado.")
    
    cur.close()
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")