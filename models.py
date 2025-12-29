from sqlalchemy import Column, Integer, String, DateTime
from database import Base
from datetime import datetime

class Operador(Base):
    __tablename__ = "operadores"
    # ... tus otros campos ...
    inspector = Column(String, default="Sin asignar")

    # Todas estas líneas DEBEN tener 4 espacios de sangría
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    fecha = Column(DateTime)
    probabilidad = Column(Integer)
    severidad = Column(Integer)
    # --- NUEVOS CAMPOS DE EXPOSICIÓN ---
    aeronaves = Column(Integer, default=0)
    vuelos_mes = Column(Integer, default=0)
    estaciones = Column(Integer, default=0)
    antiguedad = Column(Integer, default=0)
    # ----------------------------------
    hallazgos = Column(Integer, default=0)
    nivel_riesgo = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)