import os
from sqlalchemy import create_all, create_engine
# ... resto de imports

# Esto permite que use la DB de la nube si existe, o la local si no.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://usuario:password@localhost/riesgo_db")

if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
# ... resto del código