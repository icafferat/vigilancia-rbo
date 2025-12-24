import os
import sys

# Esto ayuda a Python a encontrar archivos en la carpeta actual
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
# Cambiamos el import para asegurar que lo encuentre
try:
    import models
except ImportError:
    from . import models

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def crear_admin():
    db = SessionLocal()
    # Aseguramos que las tablas existan en Render
    Base.metadata.create_all(bind=engine)
    
    # --- CONFIGURA TUS DATOS AQUÍ ---
    email_nuevo = "admin@rbo.com" 
    password_plano = "123456"
    # --------------------------------
    
    # IMPORTANTE: Revisa si tu clase en models.py se llama 'User' o 'Usuario'
    # Si se llama 'Usuario', cambia models.User por models.Usuario abajo
    usuario_existe = db.query(models.User).filter(models.User.email == email_nuevo).first()
    
    if not usuario_existe:
        hashed_pw = pwd_context.hash(password_plano)
        admin_user = models.User(
            email=email_nuevo,
            hashed_password=hashed_pw,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ Usuario {email_nuevo} creado con éxito.")
    else:
        print("⚠️ El usuario ya existe.")
    db.close()

if __name__ == "__main__":
    crear_admin()