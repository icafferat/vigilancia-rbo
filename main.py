import os
import io
import pandas as pd
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

import database
import models

# Intento de creación de tablas automático
try:
    models.Base.metadata.create_all(bind=database.engine)
except Exception as e:
    print(f"Error base de datos: {e}")

app = FastAPI()

# El Middleware de sesión DEBE ir antes de las rutas que lo usan
app.add_middleware(SessionMiddleware, secret_key="aeronautica_secret_key_2025")

USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- LÓGICA DE MATRIZ DE RIESGO ---
def calcular_riesgo_sms(p: int, s: int):
    score = p * s
    if score >= 15: return "Critico"  # Rojo (15-25)
    if score >= 6: return "Alto"      # Amarillo/Naranja (6-12)
    return "Normal"                  # Verde (1-5)

# --- RUTA DE EMERGENCIA PARA RESETEAR ---
@app.get("/reset-db-admin-2025")
async def reset_db():
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    return "✅ Base de datos reseteada con éxito. Ya puedes volver al inicio."

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

# --- DASHBOARD ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")

    operadores = db.query(models.Operador).order_by(models.Operador.fecha.desc()).all()
    # Gráfico con los 5 riesgos más altos
    top = db.query(models.Operador).order_by((models.Operador.probabilidad * models.Operador.severidad).desc()).limit(5).all()
    
    filas = ""
    for op in operadores:
        color = "#e74c3c" if op.nivel_riesgo == "Critico" else "#f39c12" if op.nivel_riesgo == "Alto" else "#27ae60"
        fecha_str = op.fecha.strftime('%d/%m/%Y') if op.fecha else 'S/F'
        filas += f"""<tr>
            <td>{fecha_str}</td>
            <td><strong>{op.nombre}</strong></td>
            <td style='text-align:center;'>{op.probabilidad}</td>
            <td style='text-align:center;'>{op.severidad}</td>
            <td style='color:{color}; font-weight:bold;'>{op.nivel_riesgo}</td>
            <td>
                <a href='/editar/{op.id}' style='text-decoration:none;'>[📝]</a> 
                <a href='/eliminar/{op.id}' style='color:red; text-decoration:none;' onclick='return confirm(\"¿Eliminar?\")'>[🗑️]</a>
            </td>
        </tr>"""

    return f"""
    <html>
        <head><title>RBO Panel</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>body{{font-family:sans-serif;margin:0;background:#f4f7f6;}} .container{{background:white;padding:25px;border-radius:10px;max-width:1050px;margin:20px auto;box-shadow:0 2px 10px rgba(0,0,0,0.05);}} table{{width:100%;border-collapse:collapse;margin-top:20px;}} th,td{{padding:12px;border-bottom:1px solid #eee;text-align:left;}} th{{background:#f8f9fa;}} .nav{{display:flex;justify-content:space-between;background:#1e3a5f;color:white;padding:15px 30px;align-items:center;}} select, input{{padding:8px; border-radius:4px; border:1px solid #ccc;}}</style></head>
        <body>
            <div class="nav"><strong>SISTEMA DE GESTIÓN DE RIESGO (MATRIZ 5X5)</strong> <div><a href="/exportar" style="color:#2ecc71;text-decoration:none;margin-right:20px;font-weight:bold;">EXCEL 📥</a><a href="/logout" style="color:white;text-decoration:none;">Cerrar Sesión</a></div></div>
            <div class="container">
                <h2>Registro de Inspecciones RBO</h2>
                <div style="background:#eef2f7; padding:20px; border-radius:8px; margin-bottom:20px;">
                    <form action="/registrar" method="post">
                        <input type="date" name="fecha" required> 
                        <input type="text" name="nombre" placeholder="Nombre Operador" required> 
                        Probabilidad: 
                        <select name="probabilidad">
                            <option value="1">1 (Muy Rara)</option><option value="2">2 (Remota)</option>
                            <option value="3">3 (Ocasional)</option><option value="4">4 (Frecuente)</option>
                            <option value="5">5 (Frecuente/Constante)</option>
                        </select>
                        Severidad: 
                        <select name="severidad">
                            <option value="1">1 (Insignificante)</option><option value="2">2 (Menor)</option>
                            <option value="3">3 (Mayor)</option><option value="4">4 (Peligrosa)</option>
                            <option value="5">5 (Catastrófica)</option>
                        </select>
                        <button type="submit" style="background:#1e3a5f; color:white; padding:8px 15px; border:none; border-radius:4px; cursor:pointer;">+ Evaluar</button>
                    </form>
                </div>
                <table><thead><tr><th>Fecha</th><th>Operador</th><th>P (Prob)</th><th>S (Sev)</th><th>Nivel Riesgo</th><th>Acciones</th></tr></thead><tbody>{filas}</tbody></table>
                <div style="margin-top:30px;"><canvas id="chart" style="max-height:250px;"></canvas></div>
            </div>
            <script>new Chart(document.getElementById('chart'),{{type:'bar',data:{{labels:{[o.nombre for o in top]},datasets:[{{label:'Puntaje de Riesgo (P x S)',data:{[o.probabilidad * o.severidad for o in top]},backgroundColor:'#e67e22'}}]}},options:{{responsive:true, maintainAspectRatio:false}}}});</script>
        </body>
    </html>
    """

# --- ACCIONES ---
@app.post("/registrar")
async def registrar(nombre: str = Form(...), probabilidad: int = Form(...), severidad: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    try:
        nivel = calcular_riesgo_sms(probabilidad, severidad)
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        nuevo = models.Operador(
            nombre=nombre, 
            hallazgos=probabilidad * severidad,
            probabilidad=probabilidad,
            severidad=severidad,
            nivel_riesgo=nivel, 
            fecha=fecha_dt
        )
        db.add(nuevo)
        db.commit()
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        print(f"Error en registro: {e}")
        return HTMLResponse(content=f"Error al registrar: {e}", status_code=500)

@app.post("/editar/{id}")
async def actualizar(id: int, nombre: str = Form(...), probabilidad: int = Form(...), severidad: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op:
        try:
            op.nombre = nombre
            op.probabilidad = probabilidad
            op.severidad = severidad
            op.nivel_riesgo = calcular_riesgo_sms(probabilidad, severidad)
            op.fecha = datetime.strptime(fecha, "%Y-%m-%d")
            db.commit()
        except Exception as e:
            print(f"Error en edición: {e}")
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op: 
        db.delete(op)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar(db: Session = Depends(get_db)):
    ops = db.query(models.Operador).all()
    if not ops: return RedirectResponse(url="/")
    data = []
    for o in ops:
        data.append({
            "Fecha": o.fecha.strftime('%Y-%m-%d') if o.fecha else "N/A",
            "Operador": o.nombre,
            "Probabilidad": o.probabilidad,
            "Severidad": o.severidad,
            "Riesgo": o.nivel_riesgo,
            "Puntaje": o.probabilidad * o.severidad
        })
    df = pd.DataFrame(data)
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        df.to_excel(w, index=False)
    out.seek(0)
    return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=matriz_riesgo.xlsx"})