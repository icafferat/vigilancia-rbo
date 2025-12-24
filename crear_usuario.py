import os
import sys
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext

# 1. Configuración de Base de Datos (Igual que en database.py)
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Definimos el modelo User aquí mismo para evitar el ImportError
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)

# 3. Configuración de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def ejecutar():
    db = SessionLocal()
    # Crea la tabla si no existe
    Base.metadata.create_all(bind=engine)
    
    # --- DATOS DEL USUARIO ---
    email_nuevo = "admin@rbo.com" 
    password_plano = "123456"
    # -------------------------

    existe = db.query(User).filter(User.email == email_nuevo).first()
    if not existe:
        hashed_pw = pwd_context.hash(password_plano)
        nuevo = User(email=email_nuevo, hashed_password=hashed_pw, is_active=True)
        db.add(nuevo)
        db.commit()
        print(f"✅ EXITO: Usuario {email_nuevo} creado.")
    else:
        print("⚠️ AVISO: El usuario ya existe en la base de datos.")
    db.close()

if __name__ == "__main__":
    ejecutar()