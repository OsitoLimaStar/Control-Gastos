import sqlite3
from flask import Flask, request, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "gastos"

con = sqlite3.connect("gastos.db", check_same_thread=False)
con.row_factory = sqlite3.Row
con.execute("CREATE TABLE IF NOT EXISTS usuario(id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE, clave_hash TEXT)")
con.execute("CREATE TABLE IF NOT EXISTS gasto(id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, descripcion TEXT, monto REAL)")
if con.execute("SELECT * FROM usuario WHERE usuario='admin'").fetchone() is None:
    con.execute("INSERT INTO usuario (usuario, clave_hash) VALUES (?,?)", ("admin", generate_password_hash("123")))
con.commit()

def login_required(v):
    @wraps(v)
    def w(*a, **k):
        if not session.get("usuario"): return redirect(url_for("login"))
        return v(*a, **k)
    return w

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = con.execute("SELECT * FROM usuario WHERE usuario=?", (request.form["usuario"],)).fetchone()
        if u and check_password_hash(u["clave_hash"], request.form["clave"]):
            session.clear()
            session["usuario"] = u["usuario"]
            return redirect(url_for("gastos"))
        return "Credenciales invalidas", 401
    return '<h1>Iniciar sesion</h1><form method="post">Usuario:<input name="usuario"><br>Clave:<input type="password" name="clave"><br><button>Ingresar</button></form>'

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/gastos", methods=["GET", "POST"])
@login_required
def gastos():
    if request.method == "POST":
        f = request.form
        partes = f["fecha"].split("-")
        try:
            monto = float(f["monto"])
        except ValueError:
            monto = -1
        if len(partes) != 3 or not all(p.isdigit() for p in partes) or f["descripcion"] == "" or monto <= 0:
            return "Datos invalidos: fecha AAAA-MM-DD, descripcion y monto mayor a 0", 400
        con.execute("INSERT INTO gasto (fecha, descripcion, monto) VALUES (?,?,?)", (f["fecha"], f["descripcion"], monto))
        con.commit()
        return redirect(url_for("gastos"))
    html = "<h1>Registrar gasto</h1><form method='post'>Fecha:<input name='fecha'><br>Descripcion:<input name='descripcion'><br>Monto:<input name='monto'><br><button>Guardar</button></form><h2>Mis gastos</h2>"
    for g in con.execute("SELECT * FROM gasto"):
        html += f"<p>{g['fecha']} | {g['descripcion']} | S/ {g['monto']}</p>"
    return html

@app.route("/reporte")
@login_required
def reporte():
    t = con.execute("SELECT SUM(monto) AS total, COUNT(*) AS n FROM gasto").fetchone()
    html = f"<h1>Reporte de gastos</h1><p>Cantidad de gastos: {t['n'] or 0}</p><p>Total gastado: S/ {t['total'] or 0}</p><h2>Detalle por fecha</h2>"
    for g in con.execute("SELECT * FROM gasto ORDER BY fecha"):
        html += f"<p>{g['fecha']} | {g['descripcion']} | S/ {g['monto']}</p>"
    return html

if __name__ == "__main__":
    app.run(debug=True)
