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
    models.Base.metadata.create_all(bind=database.engine)
    print("✅ Tablas verificadas/creadas correctamente.")
except Exception as e:
    print(f"⚠️ Error al crear tablas (posible tema de SSL): {e}")

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
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"):
        return RedirectResponse(url="/login")

    # CORRECCIÓN: Usamos models.Operador en lugar de database.Operador
    operadores = db.query(models.Operador).order_by(models.Operador.fecha.desc()).all()
    total_ops = len(operadores)
    promedio = db.query(func.avg(models.Operador.hallazgos)).scalar() or 0
    top_operadores = db.query(models.Operador).order_by(models.Operador.hallazgos.desc()).limit(5).all()
    
    nombres_top = [o.nombre for o in top_operadores]
    hallazgos_top = [o.hallazgos for o in top_operadores]
    
    filas = ""
    for op in operadores:
        color = "#e74c3c" if op.nivel_riesgo == "Critico" else "#f39c12" if op.nivel_riesgo == "Alto" else "#27ae60"
        filas += f"""
            <tr class="fila-operador">
                <td>{op.fecha.strftime("%d/%m/%Y") if op.fecha else "S/F"}</td>
                <td class="nombre-op"><strong>{op.nombre}</strong></td>
                <td style="text-align:center;">{op.hallazgos}</td>
                <td style='color:{color}; font-weight:bold;'>{op.nivel_riesgo}</td>
                <td style="text-align:right;">
                    <a href="/editar/{op.id}" style="color:#3498db; text-decoration:none; margin-right:15px;">[Editar]</a>
                    <a href="/eliminar/{op.id}" style="color:#e74c3c; text-decoration:none;" onclick="return confirm('¿Seguro?')">[X]</a>
                </td>
            </tr>
        """

    return f"""
    <html>
        <head>
            <title>RBO - Panel</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: sans-serif; margin: 0; background: #f4f7f6; }}
                .top-nav {{ background: #1e3a5f; color: white; padding: 15px; display: flex; justify-content: space-between; }}
                .container {{ max-width: 1100px; margin: 20px auto; background: white; padding: 20px; border-radius: 8px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th {{ background: #eee; padding: 10px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="top-nav">
                <span>Vigilancia RBO</span>
                <a href="/logout" style="color:white;">Cerrar Sesión</a>
            </div>
            <div class="container">
                <h2>Panel de Control</h2>
                <p>Inspecciones totales: {total_ops} | Promedio: {promedio:.1f}</p>
                
                <form action="/registrar" method="post" style="margin-bottom:20px;">
                    <input type="date" name="fecha" required>
                    <input type="text" name="nombre" placeholder="Nombre Operador" required>
                    <input type="number" name="hallazgos" placeholder="Hallazgos" required>
                    <button type="submit">Registrar</button>
                </form>

                <table>
                    <thead><tr><th>Fecha</th><th>Operador</th><th>Hallazgos</th><th>Riesgo</th><th>Acciones</th></tr></thead>
                    <tbody>{filas}</tbody>
                </table>
                <br>
                <canvas id="barChart" width="400" height="150"></canvas>
            </div>
            <script>
                new Chart(document.getElementById('barChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {nombres_top},
                        datasets: [{{ label: 'Hallazgos', data: {hallazgos_top}, backgroundColor: '#3498db' }}]
                    }}
                }});
            </script>
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

@app.post("/actualizar/{id}")
async def actualizar(id: int, request: Request, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(models.Operador).filter(models.Operador.id == id).first()
    if op:
        op.nombre = nombre
        op.hallazgos = hallazgos
        op.nivel_riesgo = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
        op.fecha = datetime.strptime(fecha, "%Y-%m-%d")
        db.commit()
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