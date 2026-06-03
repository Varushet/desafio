import pandas as pd
from sqlalchemy import create_engine
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_culture_data(csv_path: str):
    """Carga datos de cultura desde CSV a market_data.culture"""

    # Leer CSV
    df = pd.read_csv(csv_path)
    logger.info(f"Leídas {len(df)} filas del CSV")

    # Conectar a la base de datos
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    
    # Mapear columnas del CSV a la estructura de la BD
    # Primero necesitamos obtener los municipality_id desde shared.municipalities
    municipios_df = pd.read_sql("SELECT id, nombre, provincia FROM shared.municipalities", engine)
    
    # Crear diccionario para mapear (nombre, provincia) -> id
    municipio_map = {}
    for _, row in municipios_df.iterrows():
        key = (row['nombre'].strip().lower(), row['provincia'].strip().lower())
        municipio_map[key] = row['id']
    
    def get_municipio_id(nombre, provincia):
        key = (str(nombre).strip().lower(), str(provincia).strip().lower())
        return municipio_map.get(key)
    
    # Preparar datos para insertar
    records = []
    skipped = 0
    
    for _, row in df.iterrows():
        municipio_id = get_municipio_id(row['Municipio'], row['Provincia'])
        
        if not municipio_id:
            logger.warning(f"Municipio no encontrado: {row['Municipio']}, {row['Provincia']}")
            skipped += 1
            continue
        
        record = {
            'fuente': 'Manual',
            'nombre': row['Nombre'],
            'tipo_lugar': row['Tipo de lugar'],
            'tipo_cultura': row['Tipo de Cultura'],
            'descripcion': row['Descripción'],
            'precio': None,
            'horario': None,
            'telefono': str(row['Teléfono']).replace(' ', '') if pd.notna(row['Teléfono']) else None,
            'email': row['Email'],
            'web': row['WEB'],
            'web_amigable': row['URL amigable'],
            'imagen_url': row['url_imagen'],
            'municipality_id': municipio_id,
            'direccion': row['Dirección'],
            'codigo_postal': str(row['Postal Code']) if pd.notna(row['Postal Code']) else None,
            'visita_guiada': bool(row['Visita Guiada']) if pd.notna(row['Visita Guiada']) else False,
            'capacidad': int(row['Capacidad']) if pd.notna(row['Capacidad']) else None,
            'tienda': bool(row['Tienda']) if pd.notna(row['Tienda']) else False,
            'lat': float(row['lat']),
            'lng': float(row['lon']),
            'valoracion': float(row['valoracion']) if pd.notna(row['valoracion']) else None,
            'numero_valoraciones': int(row['num_resenas']) if pd.notna(row['num_resenas']) else None,
            'active': bool(row['Active']) if pd.notna(row['Active']) else True,
        }
        records.append(record)

    if not records:
        logger.error("No hay registros válidos para insertar")
        return
    
    # Insertar en batch
    culture_df = pd.DataFrame(records)
    
    try:
        culture_df.to_sql('culture', engine, schema='market_data', 
                         if_exists='append', index=False, method='multi')
        logger.info(f"Insertados {len(records)} registros correctamente")
        logger.info(f"Saltados {skipped} registros por municipio no encontrado")
    except Exception as e:
        logger.error(f"Error al insertar datos: {e}")
        raise

if __name__ == '__main__':
    load_culture_data('data/tables/cultura.csv')