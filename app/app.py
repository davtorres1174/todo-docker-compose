"""
Contenedor 1 - Aplicacion To-Do (Flask).

Se conecta a PostgreSQL (Contenedor 2) usando el NOMBRE DEL SERVICIO
definido en docker-compose.yml ("db"), nunca localhost ni una IP fija.
Todos los datos de conexion llegan por variables de entorno.
"""
import os
import time
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "db"),  # nombre del servicio en Docker
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ["POSTGRES_DB"],
    "user": os.environ["POSTGRES_USER"],
    "password": os.environ["POSTGRES_PASSWORD"],
}


def _connect(retries: int, delay: float):
    """Abre una conexion a la base de datos, reintentando si aun no esta lista."""
    last_error = None
    for _ in range(retries):
        try:
            return psycopg2.connect(**DB_CONFIG)
        except psycopg2.OperationalError as exc:
            last_error = exc
            time.sleep(delay)
    raise last_error


@contextmanager
def get_conn(retries: int = 10, delay: float = 2.0):
    """Entrega una conexion: hace commit si todo sale bien y siempre la cierra."""
    conn = _connect(retries, delay)
    try:
        with conn:  # commit / rollback automatico
            yield conn
    finally:
        conn.close()


# ---------- Vistas ----------

@app.get("/")
def index():
    return render_template("index.html", db_host=DB_CONFIG["host"])


@app.get("/health")
def health():
    """Comprueba que la app llega a la base de datos por el nombre del servicio."""
    with get_conn(retries=1) as conn, conn.cursor() as cur:
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
    return jsonify(status="ok", db_host=DB_CONFIG["host"], db_version=version)


# ---------- API REST de tareas ----------

@app.get("/api/tareas")
def listar_tareas():
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT id, titulo, completada, creada_en FROM tareas ORDER BY id;")
        tareas = cur.fetchall()
    return jsonify(tareas)


@app.post("/api/tareas")
def crear_tarea():
    datos = request.get_json(silent=True) or {}
    titulo = (datos.get("titulo") or "").strip()
    if not titulo:
        return jsonify(error="El campo 'titulo' es obligatorio"), 400
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "INSERT INTO tareas (titulo) VALUES (%s) RETURNING id, titulo, completada, creada_en;",
            (titulo,),
        )
        tarea = cur.fetchone()
    return jsonify(tarea), 201


@app.patch("/api/tareas/<int:tarea_id>")
def alternar_tarea(tarea_id: int):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            "UPDATE tareas SET completada = NOT completada WHERE id = %s "
            "RETURNING id, titulo, completada, creada_en;",
            (tarea_id,),
        )
        tarea = cur.fetchone()
    if tarea is None:
        return jsonify(error="Tarea no encontrada"), 404
    return jsonify(tarea)


@app.delete("/api/tareas/<int:tarea_id>")
def borrar_tarea(tarea_id: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM tareas WHERE id = %s;", (tarea_id,))
        borradas = cur.rowcount
    if borradas == 0:
        return jsonify(error="Tarea no encontrada"), 404
    return "", 204


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("APP_PORT", "5000")))
