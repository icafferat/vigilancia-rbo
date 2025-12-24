import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Obtenemos la URL de la base de datos de las variables de entorno de Render
# Si no existe (local), usamos una de respaldo por seguridad
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# 2. Creamos el motor de conexión
# Para PostgreSQL en Render, no necesitamos los argumentos extras de SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. Creamos la sesión (Esta es la que te pedía el error SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Creamos la base para nuestros modelos
Base = declarative_base()

# Función para obtener la base de datos (se usa en main.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()