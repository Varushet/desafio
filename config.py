import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    DB_HOST = os.getenv('DB_HOST')
    DB_NAME = os.getenv('DB_NAME')
    
    if not DB_USER or not DB_PASSWORD or not DB_NAME:
        raise ValueError("Faltan variables de entorno esenciales para la BD (DB_USER, DB_PASSWORD, DB_NAME)")

    
    # Construir la URI de conexión
    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False