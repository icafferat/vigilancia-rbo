from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import io
from datetime import datetime

import models
from database import engine, get_db

USER_ADMIN = "admin"
PASS_ADMIN = "aeronautica2025"

# --- MIGRACIÓN SILENCIOSA ---
models.Base.metadata.create_all(bind=engine)
with engine.connect() as conn:
    try:
        # Intentamos agregar la columna solo si no existe
        conn.execute(text("ALTER TABLE operadores ADD COLUMN IF NOT EXISTS inspector VARCHAR DEFAULT 'Sin asignar'"))
        conn.commit()
    except Exception as e:
        print(f"Nota: La columna inspector ya existe o no se pudo crear: {e}")

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="rbo_2026_secret_key")

def calcular_perfil_rbo(prob, sev, acft, vuelos, estaciones):
    riesgo_sms = (prob or 0) * (sev or 0)
    exp = ((acft or 0) / 5) + ((vuelos or 0) / 200) + ((estaciones or 0) / 2)
    total = riesgo_sms + exp
    if total > 35: return "Muy Alta", "#e74c3c", "Ene-Mar-May-Jul-Sep-Nov"
    if total > 18: return "Media", "#f39c12", "Feb-Jun-Oct"
    return "Baja", "#27ae60", "Junio"

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return "<html><body style='font-family:sans-serif;background:#1e3a5f;display:flex;justify-content:center;align-items:center;height:100vh;'><div style='background:white;padding:30px;border-radius:10px;'><form action='/login' method='post'><h2>SISTEMA RBO</h2><input type='text' name='username' placeholder='Usuario' required style='display:block;width:100%;margin:10px 0;padding:10px;'><input type='password' name='password' placeholder='Pass' required style='display:block;width:100%;margin:10px 0;padding:10px;'><button type='submit' style='width:100%;padding:10px;background:#3498db;color:white;border:none;cursor:pointer;'>ENTRAR</button></form></div></body></html>"

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == USER_ADMIN and password == PASS_ADMIN:
        request.session["user"] = username
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url="/login")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: Session = Depends(get_db)):
    if not request.session.get("user"): return RedirectResponse(url="/login")
    ops = db.query(models.Operador).all()
    filas = ""
    for o in ops:
        p, color, crono = calcular_perfil_rbo(o.probabilidad, o.severidad, o.aeronaves, o.vuelos_mes, o.estaciones)
        insp = getattr(o, 'inspector', 'Sin asignar') or 'Sin asignar'
        filas += f"<tr><td>{o.nombre}<br><small>Insp: {insp}</small></td><td style='color:{color}; font-weight:bold;'>{p}</td><td>{crono}</td><td><a href='/eliminar/{o.id}' style='text-decoration:none;'>🗑️</a></td></tr>"

    return f"""<html><head><title>Vigilancia RBO</title><style>body{{font-family:sans-serif;background:#f4f7f9;margin:0;}} .header{{background:#1a2a3a;color:white;padding:15px 40px;display:flex;justify-content:space-between;align-items:center;}} .container{{max-width:900px;margin:20px auto;background:white;padding:25px;border-radius:8px;}} table{{width:100%;border-collapse:collapse;margin-top:20px;}} th,td{{padding:12px;border-bottom:1px solid #eee;text-align:left;}} .btn-excel{{background:#2ecc71;color:white;padding:8px 15px;border-radius:5px;text-decoration:none;font-weight:bold;}}</style></head>
    <body><div class='header'><h2>RBO 2026</h2><div><a href='/exportar' class='btn-excel'>DESCARGAR EXCEL 📥</a><a href='/logout' style='color:white;margin-left:20px;'>Salir</a></div></div>
    <div class='container'><h3>Registrar Operador</h3><form action='/registrar' method='post' style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;'>
    <input name='inspector' placeholder='Nombre Inspector' required><input name='nombre' placeholder='Operador' required><input type='date' name='fecha' value='{datetime.now().strftime("%Y-%m-%d")}' required>
    <input type='number' name='probabilidad' placeholder='Prob (1-5)' required><input type='number' name='severidad' placeholder='Sev (1-5)' required><input type='number' name='aeronaves' placeholder='ACFT' required>
    <input type='number' name='vuelos_mes' placeholder='Vuelos' required><input type='number' name='estaciones' placeholder='Estaciones' required><button type='submit' style='background:#1a2a3a;color:white;cursor:pointer;'>GUARDAR</button></form>
    <table><thead><tr><th>Operador / Inspector</th><th>Prioridad</th><th>Plan 2026</th><th>Acción</th></tr></thead><tbody>{filas}</tbody></table></div></body></html>"""

@app.post("/registrar")
async def registrar(nombre:str=Form(...), probabilidad:int=Form(...), severidad:int=Form(...), aeronaves:int=Form(...), vuelos_mes:int=Form(...), estaciones:int=Form(...), fecha:str=Form(...), inspector:str=Form(...), db:Session=Depends(get_db)):
    nuevo = models.Operador(nombre=nombre, probabilidad=probabilidad, severidad=severidad, aeronaves=aeronaves, vuelos_mes=vuelos_mes, estaciones=estaciones, inspector=inspector, fecha=datetime.strptime(fecha, "%Y-%m-%d"))
    db.add(nuevo); db.commit(); return RedirectResponse(url="/", status_code=303)

@app.get("/eliminar/{id}")
async def eliminar(id:int, db:Session=Depends(get_db)):
    op = db.query(models.Operador).filter(models.Operador.id==id).first()
    if op: db.delete(op); db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.get("/exportar")
async def exportar_excel(db: Session = Depends(get_db)):
    try:
        ops = db.query(models.Operador).all()
        if not ops: return HTMLResponse("No hay datos")

        # Crear datos planos para evitar errores de objetos complejos
        df_data = []
        for o in ops:
            p, _, cr = calcular_perfil_rbo(o.probabilidad, o.severidad, o.aeronaves, o.vuelos_mes, o.estaciones)
            df_data.append({
                "OPERADOR": str(o.nombre),
                "INSPECTOR": str(getattr(o, 'inspector', 'N/A')),
                "PRIORIDAD": str(p),
                "CRONOGRAMA": str(cr),
                "RIESGO_SMS": int((o.probabilidad or 0) * (o.severidad or 0))
            })

        df = pd.DataFrame(df_data)
        output = io.BytesIO()
        
        # Guardar usando XlsxWriter que es más estable en Render
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Plan_Vigilancia')
            
        excel_data = output.getvalue()
        output.close()

        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="Plan_Vigilancia_RBO.xlsx"'}
        )
    except Exception as e:
        return HTMLResponse(f"Error al generar archivo: {str(e)}")