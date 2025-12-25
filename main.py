import os
import io
import pandas as pd
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from datetime import datetime

import database
import models

# Intentar crear tablas
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"Error DB: {e}")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="aeronautica_2026_key")

USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- LÓGICA RBO (RIESGO + EXPOSICIÓN) ---
def calcular_perfil_rbo(prob: int, sev: int, aviones: int, vuelos: int, estaciones: int):
    # 1. Riesgo SMS (1-25)
    sms_score = prob * sev
    
    # 2. Índice de Exposición (Simplificado 1-5)
    # Criterio: Más de 10 aviones O más de 200 vuelos O más de 5 estaciones = 5
    puntos_exp = 0
    if aviones > 10: puntos_exp += 2
    elif aviones > 3: puntos_exp += 1
    
    if vuelos > 200: puntos_exp += 2
    elif vuelos > 50: puntos_exp += 1
    
    if estaciones > 5: puntos_exp += 1
    
    expo_score = max(1, min(5, puntos_exp)) # Asegurar rango 1-5
    
    # 3. Priorización para 2026
    # Si el riesgo es crítico o la exposición es máxima
    total_prioridad = (sms_score / 5) + expo_score 
    
    if total_prioridad >= 7 or sms_score >= 15:
        return "Muy Alta", "Trimestral (4)", "#e74c3c"
    elif total_prioridad >= 4:
        return "Media", "Semestral (2)", "#f39c12"
    else:
        return "Baja", "Anual (1)", "#27ae60"

# --- RUTAS DE ACCESO ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html><head><title>RBO Login</title><style>body{font-family:sans-serif;background:#1e3a5f;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.card{background:white;padding:30px;border-radius:10px;width:320px;text-align:center;}input{width:100%;margin:10px 0;padding:12px;border:1px solid #ddd;border-radius:5px;}button{width:100%;padding:12px;background:#3498db;color:white;border:none;border-radius:5px;cursor:pointer;}</style></head>
    <body><div class="card"><h2>SISTEMA RBO 2026</h2><form action="/login" method="post"><input type="text" name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Contraseña" required><button type="submit">INGRESAR</button></form></div></body></html>
    """

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == USER_ADMIN and password == PASS_ADMIN:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse("<script>alert('Error'); window.location='/login';</script>")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# --- DASHBOARD PRINCIPAL ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")

    ops = db.query(models.Operador).order_by(models.Operador.id.desc()).all()
    
    filas = ""
    for o in ops:
        prioridad, frecuencia, color = calcular_perfil_rbo(o.probabilidad, o.severidad, o.aeronaves or 0, o.vuelos_mes or 0, o.estaciones or 0)
        filas += f"""<tr style='border-bottom: 1px solid #eee;'>
            <td>{o.nombre}</td>
            <td style='text-align:center;'>{o.probabilidad} x {o.severidad}</td>
            <td style='text-align:center;'>{o.aeronaves} Acft / {o.vuelos_mes} Ops</td>
            <td style='color:{color}; font-weight:bold;'>{prioridad}</td>
            <td style='background:#f9f9f9; font-weight:bold; text-align:center;'>{frecuencia}</td>
            <td>
                <a href='/eliminar/{o.id}' style='color:red; text-decoration:none;' onclick='return confirm(\"¿Eliminar?\")'>🗑️</a>
            </td>
        </tr>"""

    return f"""
    <html>
    <head><title>Plan 2026</title><style>
        body{{font-family:sans-serif; margin:0; background:#f4f7f6;}}
        .nav{{background:#1e3a5f; color:white; padding:15px 30px; display:flex; justify-content:space-between;}}
        .container{{max-width:1100px; margin:20px auto; background:white; padding:20px; border-radius:10px; box-shadow:0 2px 10px rgba(0,0,0,0.1);}}
        table{{width:100%; border-collapse:collapse; margin-top:20px;}}
        th, td{{padding:12px; text-align:left;}}
        th{{background:#f8f9fa; color:#333;}}
        .form-box{{background:#eef2f7; padding:20px; border-radius:8px; display:grid; grid-template-columns: repeat(3, 1fr); gap:10px;}}
        .btn{{background:#1e3a5f; color:white; border:none; padding:10px; border-radius:4px; cursor:pointer; grid-column: span 3;}}
    </style></head>
    <body>
        <div class="nav">
            <strong>PLANIFICACIÓN DE VIGILANCIA RBO 2026</strong>
            <div><a href="/exportar" style="color:#2ecc71; text-decoration:none; margin-right:15px;">DESCARGAR PLAN EXCEL 📥</a><a href="/logout" style="color:white; text-decoration:none;">Cerrar</a></div>
        </div>
        <div class="container">
            <h3>Nueva Evaluación de Perfil de Riesgo</h3>
            <form action="/registrar" method="post" class="form-box">
                <input type="text" name="nombre" placeholder="Nombre del Operador" required style="grid-column: span 2;">
                <input type="date" name="fecha" required>
                
                <div>Probabilidad (1-5):<br><input type="number" name="probabilidad" min="1" max="5" required style="width:100%;"></div>
                <div>Severidad (1-5):<br><input type="number" name="severidad" min="1" max="5" required style="width:100%;"></div>
                <div>N° Aeronaves:<br><input type="number" name="aeronaves" required style="width:100%;"></div>
                
                <div>Vuelos Mensuales:<br><input type="number" name="vuelos_mes" required style="width:100%;"></div>
                <div>N° Estaciones/Bases:<br><input type="number" name="estaciones" required style="width:100%;"></div>
                <div>Antigüedad Promedio:<br><input type="number" name="antiguedad" placeholder="Años" style="width:100%;"></div>
                
                <button type="submit" class="btn">CALCULAR PERFIL Y AGREGAR AL PLAN 2026</button>
            </form>

            <table>
                <thead>
                    <tr>
                        <th>Operador</th>
                        <th>Riesgo SMS (PxS)</th>
                        <th>Exposición (Acft/Ops)</th>
                        <th>Prioridad 2026</th>
                        <th>Frecuencia Inspección</th>
                        <th>Acciones</th>
                    </tr>
                </thead>
                <tbody>{filas}</tbody>
            </table>
        </div>
    </body>
    </html>
    """

# --- ACCIONES ---
@app.post("/registrar")
async def registrar(nombre: str = Form(...), probabilidad: int = Form(...), severidad: int = Form(...), 
                    aeronaves: int = Form(...), vuelos_mes: int = Form(...), estaciones: int = Form(...),
                    fecha: str = Form(...), db: Session = Depends(get_db)):
    nuevo = models.Operador(
        nombre=nombre, 
        probabilidad=probabilidad,
        severidad=severidad,
        aeronaves=aeronaves,
        vuelos_mes=vuelos_mes,
        estaciones=estaciones,
        fecha=datetime.strptime(fecha, "%Y-%m-%d")
    )
    db.add(nuevo); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op: db.delete(op); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar(db: Session = Depends(get_db)):
    ops = db.query(models.Operador).all()
    data = []
    for o in ops:
        prioridad, frecuencia, _ = calcular_perfil_rbo(o.probabilidad, o.severidad, o.aeronaves or 0, o.vuelos_mes or 0, o.estaciones or 0)
        data.append({
            "Operador": o.nombre,
            "Riesgo SMS": o.probabilidad * o.severidad,
            "Aeronaves": o.aeronaves,
            "Vuelos Mensuales": o.vuelos_mes,
            "Estaciones": o.estaciones,
            "Prioridad 2026": prioridad,
            "Frecuencia Sugerida": frecuencia
        })
    df = pd.DataFrame(data)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False)
    out.seek(0)
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=Plan_Vigilancia_2026.xlsx"})

# --- RUTA RESET (USAR UNA SOLA VEZ AL PEGAR ESTE CÓDIGO) ---
@app.get("/reset-db-admin-2026")
async def reset_db():
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    return "✅ Base de datos actualizada para el Plan 2026. Ve al inicio."