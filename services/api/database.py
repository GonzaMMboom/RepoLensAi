# database.py es el archivo que se encarga de la conexión a la base de datos

import os  #esto sirve para acceder a las variables de entorno

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")     #raise sirve para lanzar una excepción
engine = create_engine(DATABASE_URL, pool_pre_ping=True)    # create_engine crea el motor de la base de datos y pool_pre_ping es para que el motor de la base de datos se mantenga activo

def check_db_connection() -> None:
    """Comprueba que se puede ejecutar una consulta en PostgreSQL."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))