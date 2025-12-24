from sqlalchemy import Column, Integer, String, DateTime, Float
from database import Base
from datetime import datetime

class Operador(Base):
    __tablename__ = "operadores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    # Agrega aquí otros campos si tu app los usa, por ejemplo:
    # area = Column(String)
    # puntaje = Column(Float)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)