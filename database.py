import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. Obtenemos la URL de la variable de entorno de Render
db_url = os.getenv("DATABASE_URL")

if db_url:
    # --- CONFIGURACIÓN PARA RENDER (PostgreSQL) ---
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URL = db_url
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # --- CONFIGURACIÓN PARA TU IMAC (SQLite) ---
    SQLALCHEMY_DATABASE_URL = "sqlite:///./rbo_local.db"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, 
        connect_args={"check_same_thread": False}
    )

# --- MIGRACIÓN AUTOMÁTICA DE LA COLUMNA INSPECTOR ---
# Este bloque detecta si falta la columna y la crea sin borrar tus datos
with engine.connect() as conn:
    try:
        # Comando universal que funciona en SQLite y PostgreSQL
        conn.execute(text("ALTER TABLE operadores ADD COLUMN inspector VARCHAR DEFAULT 'Sin asignar'"))
        conn.commit()
        print("✅ Columna 'inspector' verificada/añadida.")
    except Exception as e:
        # Si la columna ya existe, fallará silenciosamente (lo cual está bien)
        print(f"ℹ️ Nota sobre DB: {e}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()