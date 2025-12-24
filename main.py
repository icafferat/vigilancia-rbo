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

import database
import models

# Creación de tablas
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"Error base de datos: {e}")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="aeronautica_secret_key_2025")

USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- LOGIN ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html>
        <head><title>Acceso - RBO</title><style>body{font-family:sans-serif;background:#1e3a5f;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.card{background:white;padding:30px;border-radius:10px;width:320px;text-align:center;box-shadow:0 10px 25px rgba(0,0,0,0.3);}input{width:100%;margin:10px 0;padding:12px;border:1px solid #ddd;border-radius:5px;box-sizing:border-box;}button{width:100%;padding:12px;background:#3498db;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold;}</style></head>
        <body><div class="card"><h2>SISTEMA RBO</h2><form action="/login" method="post"><input type="text" name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Contraseña" required><button type="submit">INGRESAR</button></form></div></body>
    </html>
    """

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == USER_ADMIN and password == PASS_ADMIN:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse("<script>alert('Credenciales incorrectas'); window.location='/login';</script>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# --- DASHBOARD (LA RUTA QUE ESTABA DANDO 404) ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")

    operadores = db.query(models.Operador).order_by(models.Operador.fecha.desc()).all()
    total = len(operadores)
    promedio = db.query(func.avg(models.Operador.hallazgos)).scalar() or 0
    top = db.query(models.Operador).order_by(models.Operador.hallazgos.desc()).limit(5).all()
    
    filas = ""
    for op in operadores:
        color = "#e74c3c" if op.nivel_riesgo == "Critico" else "#f39c12" if op.nivel_riesgo == "Alto" else "#27ae60"
        filas += f"<tr><td>{op.fecha.strftime('%d/%m/%Y') if op.fecha else 'S/F'}</td><td><strong>{op.nombre}</strong></td><td>{op.hallazgos}</td><td style='color:{color}; font-weight:bold;'>{op.nivel_riesgo}</td><td><a href='/editar/{op.id}' style='text-decoration:none;'>[📝]</a> <a href='/eliminar/{op.id}' style='color:red; text-decoration:none;' onclick='return confirm(\"¿Eliminar?\")'>[🗑️]</a></td></tr>"

    return f"""
    <html>
        <head><title>RBO Panel</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>body{{font-family:sans-serif;margin:0;background:#f4f7f6;}} .container{{background:white;padding:25px;border-radius:10px;max-width:1050px;margin:20px auto;box-shadow:0 2px 10px rgba(0,0,0,0.05);}} table{{width:100%;border-collapse:collapse;margin-top:20px;}} th,td{{padding:12px;border-bottom:1px solid #eee;text-align:left;}} th{{background:#f8f9fa;}} .nav{{display:flex;justify-content:space-between;background:#1e3a5f;color:white;padding:15px 30px;align-items:center;}}</style></head>
        <body>
            <div class="nav"><strong>VIGILANCIA RIESGO AÉREO</strong> <div><a href="/exportar" style="color:#2ecc71;text-decoration:none;margin-right:20px;font-weight:bold;">EXCEL 📥</a><a href="/logout" style="color:white;text-decoration:none;">Cerrar Sesión</a></div></div>
            <div class="container">
                <h2>Panel de Control</h2>
                <div style="background:#eef2f7; padding:15px; border-radius:8px; margin-bottom:20px;">
                    <form action="/registrar" method="post">
                        <input type="date" name="fecha" required> 
                        <input type="text" name="nombre" placeholder="Nombre Operador" required style="padding:5px;"> 
                        <input type="number" name="hallazgos" placeholder="Hallazgos" required style="width:100px; padding:5px;"> 
                        <button type="submit" style="background:#1e3a5f; color:white; padding:6px 15px; border:none; border-radius:4px; cursor:pointer;">+ Registrar</button>
                    </form>
                </div>
                <table><thead><tr><th>Fecha</th><th>Operador</th><th>Hallazgos</th><th>Riesgo</th><th>Acciones</th></tr></thead><tbody>{filas}</tbody></table>
                <div style="margin-top:30px;"><canvas id="chart" style="max-height:250px;"></canvas></div>
            </div>
            <script>new Chart(document.getElementById('chart'),{{type:'bar',data:{{labels:{[o.nombre for o in top]},datasets:[{{label:'Hallazgos por Operador',data:{[o.hallazgos for o in top]},backgroundColor:'#3498db'}}]}},options:{{responsive:true, maintainAspectRatio:false}}}});</script>
        </body>
    </html>
    """

# --- PÁGINA DE EDICIÓN (GET) ---
@app.get("/editar/{id}", response_class=HTMLResponse)
async def editar_page(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if not op: return RedirectResponse(url="/")
    return f"""
    <html><body style="font-family:sans-serif;padding:50px;background:#f4f7f6;">
    <div style="max-width:400px;margin:auto;background:white;padding:30px;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
        <h3 style="color:#1e3a5f;">Editar Operador</h3><hr>
        <form action="/editar/{op.id}" method="post">
            <label>Fecha:</label><br><input type="date" name="fecha" value="{op.fecha.strftime('%Y-%m-%d') if op.fecha else ''}" required style="width:100%;margin:10px 0;padding:8px;"><br>
            <label>Nombre:</label><br><input type="text" name="nombre" value="{op.nombre}" required style="width:100%;margin:10px 0;padding:8px;"><br>
            <label>Hallazgos:</label><br><input type="number" name="hallazgos" value="{op.hallazgos}" required style="width:100%;margin:10px 0;padding:8px;"><br>
            <button type="submit" style="width:100%;background:#3498db;color:white;border:none;padding:12px;border-radius:5px;cursor:pointer;font-weight:bold;margin-top:10px;">GUARDAR CAMBIOS</button>
        </form>
        <div style="text-align:center; margin-top:15px;"><a href="/" style="color:#666;text-decoration:none;">← Cancelar y volver</a></div>
    </div></body></html>
    """

# --- ACCIONES ---
@app.post("/registrar")
async def registrar(nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    nivel = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
    nuevo = models.Operador(nombre=nombre, hallazgos=hallazgos, nivel_riesgo=nivel, fecha=datetime.strptime(fecha, "%Y-%m-%d"))
    db.add(nuevo); db.commit(); return RedirectResponse(url="/", status_code=303)

@app.post("/editar/{id}")
async def actualizar(id: int, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op:
        op.nombre, op.hallazgos = nombre, hallazgos
        op.nivel_riesgo = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
        op.fecha = datetime.strptime(fecha, "%Y-%m-%d")
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op: db.delete(op); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar(db: Session = Depends(get_db)):
    ops = db.query(models.Operador).all()
    if not ops: return RedirectResponse(url="/")
    df = pd.DataFrame([{"Fecha": o.fecha, "Operador": o.nombre, "Hallazgos": o.hallazgos, "Riesgo": o.nivel_riesgo} for o in ops])
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
    out.seek(0)
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=reporte_vuelo.xlsx"})