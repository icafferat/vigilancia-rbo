import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Obtenemos la URL de la variable de entorno de Render
db_url = os.getenv("DATABASE_URL")

if db_url:
    # --- CONFIGURACIÓN PARA RENDER (PostgreSQL) ---
    # Render a veces entrega postgres://, pero SQLAlchemy requiere postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    
    SQLALCHEMY_DATABASE_URL = db_url
    # No necesitamos argumentos extra para Postgres
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # --- CONFIGURACIÓN PARA TU IMAC (SQLite) ---
    SQLALCHEMY_DATABASE_URL = "sqlite:///./rbo_local.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función para obtener la sesión (utilizada en main.py)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()