import pandas as pd
import json
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

DB_URI = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
engine = create_engine(DB_URI)


def load_csv_to_table(csv_path: str, table_name: str, schema: str = 'market_data', **read_kwargs):
    if not os.path.exists(csv_path):
        print(f"❌ Archivo no encontrado: {csv_path}")
        return

    try:
        # 1. Leer CSV con parámetros específicos
        df = pd.read_csv(csv_path, on_bad_lines='warn', **read_kwargs)

        # 2. Limpieza específica por tabla
        # Las tablas con PK SERIAL generan su propio ID, así que descartamos la columna 'id' del CSV si existe
        if table_name in ['gastronomy', 'culture']:
            if 'id' in df.columns:
                df = df.drop(columns=['id'])
        
        # Para 'events', el ID es VARCHAR y viene en el CSV, así que lo mantenemos tal cual.

        # 3. Procesar columnas JSONB (común a varias tablas si las tuviera)
        json_cols = ['images', 'attachment']
        for col in json_cols:
            if col in df.columns:
                # Convertir string JSON a objeto Python para que SQLAlchemy lo maneje como JSONB
                df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) and isinstance(x, str) else x)

        # 4. Insertar en BD
        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists='append',
            index=False,       # No guardar el índice de pandas como columna
            method='multi',
            chunksize=1000
        )

        print(f"✅ {len(df)} registros insertados en {schema}.{table_name}")

    except Exception as e:
        print(f"❌ Error cargando {csv_path} en {table_name}: {e}")
        # Opcional: imprimir las primeras filas para depurar
        # print(df.head())


# === EJECUCIÓN ===

# 1. Events (ID alfanumérico, fechas complejas)
load_csv_to_table(
    'data/tables/events_preprocessed.csv', 
    'events', 
    dtype={'id': str},
    parse_dates=['start_date', 'end_date', 'publication_date']
)

# 2. Gastronomy (ID Serial, sin fechas especiales)
load_csv_to_table(
    'data/tables/gastronomy_preprocessed.csv', 
    'gastronomy'
)

# 3. Culture (ID Serial, sin fechas especiales)
load_csv_to_table(
    'data/tables/culture_preprocessed.csv', 
    'culture'
)