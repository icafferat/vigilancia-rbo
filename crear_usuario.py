import os
import sys
from sqlalchemy import Column, Integer, String, Boolean, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Intentar importar passlib, si no está, usamos un placeholder
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    HAS_PASSLIB = True
except ImportError:
    HAS_PASSLIB = False
    print("⚠️ ADVERTENCIA: Passlib no instalado. La contraseña se guardará en texto plano (solo para emergencia).")

# ... (resto del código igual que antes) ...

    if not existe:
        # Si tenemos passlib lo hasheamos, si no, lo guardamos directo para poder entrar
        if HAS_PASSLIB:
            hashed_pw = pwd_context.hash(password_plano)
        else:
            hashed_pw = password_plano # Emergencia total
            
        nuevo = User(email=email_nuevo, hashed_password=hashed_pw, is_active=True)
        # ... (db.add, db.commit, etc)