import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Intentamos obtener la URL de la nube
db_url = os.getenv("DATABASE_URL")

# 2. Lógica Inteligente
if db_url is not None:
    # SI ESTAMOS EN RENDER (Nube)
    # Corregimos el prefijo si es necesario
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    # Aseguramos el modo SSL para PostgreSQL
    if "?sslmode=" not in db_url:
        db_url += "?sslmode=require"
    
    SQLALCHEMY_DATABASE_URL = "postgresql://admin_rbo:xBBOpHjvMvlYeySU2Q0rs8H5koqJSTBi@dpg-d55mi0mmcj7s73fecir0-a.virginia-postgres.render.com/rbo_db_4pe8"
    # Para Postgres no necesitamos argumentos extra
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # SI ESTAMOS EN TU IMAC (Local)
    # Usamos SQLite y creamos un archivo local
    SQLALCHEMY_DATABASE_URL = "sqlite:///./rbo_local.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False} # Necesario solo para SQLite
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()