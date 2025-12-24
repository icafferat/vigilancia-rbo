import os
import io
import pandas as pd
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

# Importamos nuestros archivos locales
import database
import models

# Intentamos crear las tablas automáticamente al iniciar
try:
    print("Intentando conectar a la base de datos...")
    models.Base.metadata.create_all(bind=database.engine)
    print("✅ Conexión exitosa y tablas creadas/verificadas.")
except Exception as e:
    print(f"❌ ERROR CRÍTICO AL CREAR TABLAS: {e}")

app = FastAPI()

# Clave de cifrado para las sesiones (Obligatorio para usar request.session)
app.add_middleware(SessionMiddleware, secret_key="aeronautica_secret_key_2025")

# Credenciales de acceso
USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- VISTA DE LOGIN ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html>
        <head>
            <title>Acceso Institucional - RBO</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #1e3a5f 0%, #2c3e50 100%); display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
                .login-card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 15px 35px rgba(0,0,0,0.4); width: 380px; text-align: center; }
                .login-card h2 { color: #1e3a5f; margin-bottom: 10px; font-size: 24px; }
                input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <h2>VIGILANCIA AÉREA</h2>
                <form action="/login" method="post">
                    <input type="text" name="username" placeholder="Usuario Institucional" required>
                    <input type="password" name="password" placeholder="Contraseña" required>
                    <button type="submit">INGRESAR AL SISTEMA</button>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == USER_ADMIN and password == PASS_ADMIN:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse("<script>alert('Credenciales Incorrectas'); window.location='/login';</script>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# --- DASHBOARD PRINCIPAL ---
@app.get("/editar/{id}", response_class=HTMLResponse)
async def editar_page(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): 
        return RedirectResponse(url="/login")
    
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if not op:
        return HTMLResponse("<h2>Operador no encontrado</h2><a href='/'>Volver</a>")

    # Formulario con los datos cargados
    return f"""
    <html>
        <head><title>Editar Registro</title></head>
        <body style="font-family:sans-serif; padding:50px; background:#f4f7f6;">
            <div style="max-width:500px; margin:auto; background:white; padding:30px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.1);">
                <h2>Editar Operador</h2>
                <form action="/editar/{op.id}" method="post">
                    <label>Fecha:</label><br>
                    <input type="date" name="fecha" value="{op.fecha.strftime('%Y-%m-%d')}" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <label>Nombre:</label><br>
                    <input type="text" name="nombre" value="{op.nombre}" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <label>Hallazgos:</label><br>
                    <input type="number" name="hallazgos" value="{op.hallazgos}" required style="width:100%; padding:10px; margin:10px 0;"><br>
                    <button type="submit" style="background:#3498db; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer;">Guardar Cambios</button>
                    <a href="/" style="margin-left:10px; color:#666;">Cancelar</a>
                </form>
            </div>
        </body>
    </html>
    """

# --- ACCIONES ---
@app.post("/registrar")
async def registrar(request: Request, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    nivel = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
    # CORRECCIÓN: Usamos models.Operador
    nuevo_op = models.Operador(nombre=nombre, hallazgos=hallazgos, nivel_riesgo=nivel, fecha=datetime.strptime(fecha, "%Y-%m-%d"))
    db.add(nuevo_op)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op:
        db.delete(op)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/editar/{id}")
async def actualizar(id: int, request: Request, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"): 
        return RedirectResponse(url="/login")
    
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    
    if op:
        op.nombre = nombre
        op.hallazgos = hallazgos
        # Lógica de riesgo
        op.nivel_riesgo = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
        # Conversión de fecha
        op.fecha = datetime.strptime(fecha, "%Y-%m-%d")
        
        db.commit()
    
    # El status_code=303 es fundamental para que el navegador cambie de POST a GET al redirigir
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    operadores = db.query(models.Operador).all()
    data = [{"Fecha": o.fecha, "Operador": o.nombre, "Hallazgos": o.hallazgos} for o in operadores]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return StreamingResponse(output, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=reporte.xlsx"})