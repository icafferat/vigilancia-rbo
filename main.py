from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import io
from datetime import datetime

# Importes de tus archivos locales
import database
import models
from database import engine, get_db
USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

# Crear tablas si no existen
models.Base.metadata.create_all(bind=engine)

app = FastAPI()
# Necesario para el Login
app.add_middleware(SessionMiddleware, secret_key="rbo_2026_secret_key")

# --- LÓGICA DE CÁLCULO RBO Y CALENDARIO ---
# Definirla aquí arriba evita errores de "function not defined"
def calcular_perfil_rbo(prob, sev, acft, vuelos, estaciones):
    riesgo_sms = (prob or 0) * (sev or 0)
    # Factor de exposición: basado en tamaño de flota y operaciones
    exp = ((acft or 0) / 5) + ((vuelos or 0) / 200) + ((estaciones or 0) / 2)
    total = riesgo_sms + exp

    if total > 35:
        prioridad, color = "Muy Alta", "#e74c3c"
        cronograma = "Ene: BASE PRINCIPAL | Mar: PLATAFORMA | May: RUTA | Jul: ESTACIÓN | Sep: REGISTROS | Nov: CABINA"
    elif total > 18:
        prioridad, color = "Media", "#f39c12"
        cronograma = "Feb: BASE PRINCIPAL | Jun: PLATAFORMA | Oct: IDE"
    else:
        prioridad, color = "Baja", "#27ae60"
        cronograma = "Jun: PLATAFORMA o RUTA"
        
    return prioridad, color, cronograma

# --- RUTAS DE ACCESO ---
@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return """
    <html><head><title>RBO Login</title><style>body{font-family:sans-serif;background:#1e3a5f;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;}.card{background:white;padding:30px;border-radius:10px;width:320px;text-align:center;}input{width:100%;margin:10px 0;padding:12px;border:1px solid #ddd;border-radius:5px;}button{width:100%;padding:12px;background:#3498db;color:white;border:none;border-radius:5px;cursor:pointer;}</style></head>
    <body><div class="card"><h2>SISTEMA RBO 2026</h2><form action="/login" method="post"><input type="text" name="username" placeholder="Usuario" required><input type="password" name="password" placeholder="Contraseña" required><button type="submit">INGRESAR</button></form></div></body></html>
    """

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    # Agregamos comillas y los dos puntos finales
    if username == USER_ADMIN and password == PASS_ADMIN:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    
    # Respuesta en caso de error
    return HTMLResponse("<script>alert('Usuario o contraseña incorrectos'); window.location='/login';</script>")
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

# --- DASHBOARD PRINCIPAL ---
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")

    ops = db.query(models.Operador).all()
    
    conteos = {"Muy Alta": 0, "Media": 0, "Baja": 0}
    nombres_labels = []
    puntajes_sms = []
    
    filas = ""
    for o in ops:
        prioridad, color, cronograma = calcular_perfil_rbo(
            o.probabilidad, o.severidad, o.aeronaves or 0, o.vuelos_mes or 0, o.estaciones or 0
        )
        
        conteos[prioridad] += 1
        nombres_labels.append(o.nombre)
        puntajes_sms.append(o.probabilidad * o.severidad)
        
        filas += f"""
        <tr style='border-bottom: 1px solid #eee;'>
            <td style='padding:15px;'><strong>{o.nombre}</strong></td>
            <td style='text-align:center;'><span style='background:{color}; color:white; padding:5px 10px; border-radius:15px; font-size:12px;'>{prioridad}</span></td>
            <td><div style='background:#f8f9fa; border-left:4px solid {color}; padding:10px; border-radius:4px; font-size:13px;'>{cronograma}</div></td>
            <td style='text-align:center;'><a href='/eliminar/{o.id}' style='text-decoration:none;'>🗑️</a></td>
        </tr>"""

    return f"""
    <html>
    <head>
        <title>RBO 2026</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: sans-serif; background:#f4f7f9; margin:0; }}
            .header {{ background:#1a2a3a; color:white; padding:15px 40px; display:flex; justify-content:space-between; align-items:center; }}
            .container {{ max-width:1100px; margin:20px auto; background:white; padding:25px; border-radius:10px; }}
            .form-section {{ background:#eef2f7; padding:20px; border-radius:8px; margin-bottom:20px; }}
            .grid-form {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; }}
            input, button {{ padding:10px; border-radius:5px; border:1px solid #ccc; }}
            button {{ background:#1a2a3a; color:white; cursor:pointer; font-weight:bold; }}
            table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
            th {{ background:#f1f4f7; padding:12px; text-align:left; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>VIGILANCIA RBO 2026</h2>
            <div>
                <a href="/exportar" style="color:#2ecc71; text-decoration:none; margin-right:20px; font-weight:bold;">EXCEL 📥</a>
                <a href="/logout" style="color:white; text-decoration:none;">Cerrar</a>
            </div>
        </div>
        <div class="container">
            <div class="form-section">
                <h3>Nuevo Registro de Operador</h3>
                <form action="/registrar" method="post" class="grid-form">
                    <input type="text" name="nombre" placeholder="Nombre Operador" required style="grid-column: span 2;">
                    <input type="date" name="fecha" required>
                    <input type="number" name="probabilidad" placeholder="Prob. SMS (1-5)" min="1" max="5" required>
                    <input type="number" name="severidad" placeholder="Sev. SMS (1-5)" min="1" max="5" required>
                    <input type="number" name="aeronaves" placeholder="N° Aeronaves" required>
                    <input type="number" name="vuelos_mes" placeholder="Vuelos Mensuales" required>
                    <input type="number" name="estaciones" placeholder="N° Estaciones" required>
                    <button type="submit" style="grid-column: span 3;">CALCULAR Y AGREGAR AL PLAN</button>
                </form>
            </div>

            <table>
                <thead><tr><th>Operador</th><th>Prioridad</th><th>Cronograma 2026</th><th>Acción</th></tr></thead>
                <tbody>{filas}</tbody>
            </table>

            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:30px;">
                <canvas id="pieChart"></canvas>
                <canvas id="barChart"></canvas>
            </div>
        </div>
        <script>
            new Chart(document.getElementById('pieChart'), {{ type: 'doughnut', data: {{ labels: ['Muy Alta', 'Media', 'Baja'], datasets: [{{ data: [{conteos['Muy Alta']}, {conteos['Media']}, {conteos['Baja']}], backgroundColor: ['#e74c3c', '#f39c12', '#27ae60'] }}] }} }});
            new Chart(document.getElementById('barChart'), {{ type: 'bar', data: {{ labels: {nombres_labels}, datasets: [{{ label: 'Riesgo SMS', data: {puntajes_sms}, backgroundColor: '#3498db' }}] }} }});
        </script>
    </body>
    </html>
    """
# --- ACCIONES ---
@app.post("/registrar")
async def registrar(nombre: str = Form(...), probabilidad: int = Form(...), 
                    severidad: int = Form(...), aeronaves: int = Form(...), 
                    vuelos_mes: int = Form(...), estaciones: int = Form(...),
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
    db.add(nuevo)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, db: Session = Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op: db.delete(op); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar_excel(db: Session = Depends(get_db)):
    ops = db.query(models.Operador).all()
    
    data = []
    for o in ops:
        prioridad, color, cronograma = calcular_perfil_rbo(
            o.probabilidad, o.severidad, o.aeronaves or 0, o.vuelos_mes or 0, o.estaciones or 0
        )
        
        data.append({
            "Operador": o.nombre,
            "Fecha Evaluación": o.fecha,
            "Probabilidad SMS": o.probabilidad,
            "Severidad SMS": o.severidad,
            "Puntaje Riesgo": o.probabilidad * o.severidad,
            "Aeronaves": o.aeronaves,
            "Vuelos/Mes": o.vuelos_mes,
            "Prioridad 2026": prioridad,
            "Cronograma Sugerido": cronograma
        })

    df = pd.DataFrame(data)
    
    # Crear un archivo Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Plan Vigilancia 2026')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="Plan_Vigilancia_RBO_2026.xlsx"'
    }
    
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')