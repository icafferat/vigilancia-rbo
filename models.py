from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class Operador(Base):
    __tablename__ = "operadores"

    # Todas estas líneas DEBEN tener 4 espacios de sangría
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    fecha = Column(DateTime)
    hallazgos = Column(Integer, default=0)
    probabilidad = Column(Integer, default=1)  # Escala 1-5
    severidad = Column(Integer, default=1)     # Escala 1-5
    nivel_riesgo = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)