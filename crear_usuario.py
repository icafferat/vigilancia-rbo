from database import SessionLocal, engine, Base
import models
from passlib.context import CryptContext

# Configuración de seguridad para la contraseña
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def crear_admin():
    db = SessionLocal()
    # 1. Asegurarnos de que las tablas existan
    Base.metadata.create_all(bind=engine)
    
    # 2. Datos de tu nuevo usuario
    email_nuevo = "icafferata@icloud.com" 
    password_plano = "aeronauticacivil"   
    
    # 3. Verificar si ya existe para no duplicarlo
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