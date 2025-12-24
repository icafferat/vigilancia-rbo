import os
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
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

# Clave de cifrado para las sesiones
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

# --- VISTA DE LOGIN PERSONALIZADA ---
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
                .login-card p { color: #7f8c8d; margin-bottom: 25px; font-size: 14px; }
                input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; box-sizing: border-box; }
                button { width: 100%; padding: 12px; background: #3498db; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 16px; transition: 0.3s; }
                button:hover { background: #2980b9; }
                .footer-text { margin-top: 20px; font-size: 11px; color: #bdc3c7; }
            </style>
        </head>
        <body>
            <div class="login-card">
                <h2>VIGILANCIA AÉREA</h2>
                <p>Sistema de Gestión Basada en Riesgo (RBO)</p>
                <form action="/login" method="post">
                    <input type="text" name="username" placeholder="Usuario Institucional" required>
                    <input type="password" name="password" placeholder="Contraseña" required>
                    <button type="submit">INGRESAR AL SISTEMA</button>
                </form>
                <div class="footer-text">Acceso restringido a personal autorizado</div>
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

    operadores = db.query(models.Operador).order_by(models.Operador.fecha.desc()).all()
    total_ops = len(operadores)
    promedio = db.query(func.avg(database.Operador.hallazgos)).scalar() or 0
    top_operadores = db.query(database.Operador).order_by(database.Operador.hallazgos.desc()).limit(5).all()
    
    nombres_top = [o.nombre for o in top_operadores]
    hallazgos_top = [o.hallazgos for o in top_operadores]
    
    filas = ""
    for op in operadores:
        color = "#e74c3c" if op.nivel_riesgo == "Critico" else "#f39c12" if op.nivel_riesgo == "Alto" else "#27ae60"
        filas += f"""
            <tr class="fila-operador">
                <td>{op.fecha.strftime("%d/%m/%Y")}</td>
                <td class="nombre-op"><strong>{op.nombre}</strong></td>
                <td style="text-align:center;">{op.hallazgos}</td>
                <td style='color:{color}; font-weight:bold;'>{op.nivel_riesgo}</td>
                <td style="text-align:right;">
                    <a href="/editar/{op.id}" style="color:#3498db; text-decoration:none; margin-right:15px; font-size:13px;">[Editar]</a>
                    <a href="/eliminar/{op.id}" style="color:#e74c3c; text-decoration:none; font-size:13px;" onclick="return confirm('¿Seguro que desea eliminar?')">[X]</a>
                </td>
            </tr>
        """

    return f"""
    <html>
        <head>
            <title>RBO - Panel de Control</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; margin: 0; background-color: #f8f9fa; }}
                .top-nav {{ background: #1e3a5f; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
                .container {{ max-width: 1200px; margin: 30px auto; padding: 0 20px; }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); text-align: center; border-top: 4px solid #3498db; }}
                .main-grid {{ display: grid; grid-template-columns: 2fr 1fr; gap: 20px; }}
                .panel {{ background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
                th {{ text-align: left; background: #f1f4f7; padding: 12px; color: #2c3e50; font-size: 14px; }}
                td {{ padding: 12px; border-bottom: 1px solid #eee; font-size: 14px; }}
                .btn-excel {{ background: #27ae60; color: white; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-size: 14px; }}
                .form-section {{ background: #fff; padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="top-nav">
                <h2 style="margin:0;">Vigilancia Basada en Riesgos</h2>
                <div>
                    <span style="font-size:14px; margin-right:20px;">Usuario: <strong>{request.session.get('user')}</strong></span>
                    <a href="/logout" style="color:#ff7675; text-decoration:none; font-weight:bold;">Cerrar Sesión</a>
                </div>
            </div>

            <div class="container">
                <div class="stats-grid">
                    <div class="stat-card"> <small>Total Inspecciones</small> <h2 style="margin:10px 0; color:#1e3a5f;">{total_ops}</h2> </div>
                    <div class="stat-card"> <small>Promedio Hallazgos</small> <h2 style="margin:10px 0; color:#3498db;">{promedio:.1f}</h2> </div>
                    <div class="stat-card" style="border-top-color:#27ae60;"> 
                        <a href="/exportar" class="btn-excel" style="display:inline-block; margin-top:15px;">Descargar Reporte Excel</a>
                    </div>
                </div>

                <div class="main-grid">
                    <div class="panel">
                        <h3>Registro de Inspecciones</h3>
                        <div class="form-section">
                            <form action="/registrar" method="post" style="display:flex; gap:10px;">
                                <input type="date" name="fecha" required style="padding:8px;">
                                <input type="text" name="nombre" placeholder="Nombre Operador (AOC)" required style="flex:2; padding:8px;">
                                <input type="number" name="hallazgos" placeholder="Hallazgos" required style="flex:1; padding:8px;">
                                <button type="submit" style="background:#1e3a5f; color:white; border:none; padding:10px 20px; border-radius:4px; cursor:pointer;">Registrar</button>
                            </form>
                        </div>
                        
                        <input type="text" id="buscador" onkeyup="filtrar()" placeholder="🔍 Buscar operador por nombre..." style="width:100%; padding:10px; margin-bottom:15px; border:1px solid #ddd; border-radius:4px;">
                        
                        <table>
                            <thead>
                                <tr><th>Fecha</th><th>Operador</th><th style="text-align:center;">Hallazgos</th><th>Riesgo</th><th style="text-align:right;">Acciones</th></tr>
                            </thead>
                            <tbody>{filas}</tbody>
                        </table>
                    </div>
                    
                    <div class="panel">
                        <h3>Análisis Comparativo</h3>
                        <p style="font-size:12px; color:#7f8c8d;">Top 5 Operadores con mayor nivel de hallazgos encontrados.</p>
                        <canvas id="barChart" style="height:300px;"></canvas>
                    </div>
                </div>
            </div>

            <script>
                function filtrar() {{
                    let val = document.getElementById('buscador').value.toUpperCase();
                    let filas = document.getElementsByClassName('fila-operador');
                    for (let f of filas) {{ f.style.display = f.innerText.toUpperCase().includes(val) ? "" : "none"; }}
                }}
                
                const ctx = document.getElementById('barChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'bar',
                    data: {{
                        labels: {nombres_top},
                        datasets: [{{
                            label: 'Cantidad de Hallazgos',
                            data: {hallazgos_top},
                            backgroundColor: 'rgba(52, 152, 219, 0.8)',
                            borderColor: '#2980b9',
                            borderWidth: 1
                        }}]
                    }},
                    options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
                }});
            </script>
        </body>
    </html>
    """

# --- RUTAS DE ACCIÓN PROTEGIDAS (IDÉNTICAS A LAS ANTERIORES) ---
@app.post("/registrar")
async def registrar(request: Request, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    nivel = "Critico" if hallazgos > 10 else "Alto" if hallazgos > 5 else "Normal"
    nuevo_op = database.Operador(nombre=nombre, hallazgos=hallazgos, nivel_riesgo=nivel, fecha=datetime.strptime(fecha, "%Y-%m-%d"))
    db.add(nuevo_op)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(database.Operador).filter(database.Operador.id == id).first()
    if op:
        db.delete(op)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/editar/{id}", response_class=HTMLResponse)
async def form_editar(id: int, request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(database.Operador).filter(database.Operador.id == id).first()
    fecha_val = op.fecha.strftime("%Y-%m-%d") if op.fecha else ""
    return f"""
    <html>
        <body style="font-family:sans-serif; background:#2c3e50; display:flex; justify-content:center; align-items:center; height:100vh; margin:0;">
            <div style="background:white; padding:30px; border-radius:10px; width:350px;">
                <h3 style="color:#1e3a5f;">Actualizar Registro</h3>
                <form action="/actualizar/{id}" method="post">
                    <input type="date" name="fecha" value="{fecha_val}" required style="width:100%; padding:10px; margin-bottom:10px;">
                    <input type="text" name="nombre" value="{op.nombre}" required style="width:100%; padding:10px; margin-bottom:10px;">
                    <input type="number" name="hallazgos" value="{op.hallazgos}" required style="width:100%; padding:10px; margin-bottom:10px;">
                    <button type="submit" style="width:100%; padding:10px; background:#27ae60; color:white; border:none; border-radius:4px; cursor:pointer;">Guardar Cambios</button>
                    <a href="/" style="display:block; text-align:center; margin-top:15px; color:#666; font-size:13px; text-decoration:none;">Volver al Panel</a>
                </form>
            </div>
        </body>
    </html>
    """

@app.post("/actualizar/{id}")
async def actualizar(id: int, request: Request, nombre: str = Form(...), hallazgos: int = Form(...), fecha: str = Form(...), db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    op = db.query(database.Operador).filter(database.Operador.id == id).first()
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
    operadores = db.query(database.Operador).all()
    data = [{"Fecha": o.fecha.strftime("%d/%m/%Y"), "Operador": o.nombre, "Hallazgos": o.hallazgos, "Riesgo": o.nivel_riesgo} for o in operadores]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return StreamingResponse(output, headers={"Content-Disposition": "attachment; filename=Reporte_RBO.xlsx"}, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")