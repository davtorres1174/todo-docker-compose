"""
Pruebas unitarias de la API To-Do.

No necesitan PostgreSQL: la conexion se reemplaza por una base de datos
falsa en memoria (FakeDB), asi que corren en segundos dentro de un
contenedor efimero de Python en el pipeline de Jenkins.
"""
import os
import sys
from contextlib import contextmanager
from datetime import datetime

import pytest

# app.py lee estas variables al importarse; en las pruebas usamos valores ficticios
os.environ.setdefault("POSTGRES_DB", "test_db")
os.environ.setdefault("POSTGRES_USER", "test_user")
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402


class FakeDB:
    """Imita la tabla 'tareas' de PostgreSQL con una lista en memoria."""

    def __init__(self):
        self.tareas = []
        self.next_id = 1


class FakeCursor:
    def __init__(self, db):
        self.db = db
        self._result = None
        self.rowcount = 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=()):
        sql = sql.strip().upper()
        if sql.startswith("SELECT VERSION"):
            self._result = [("PostgreSQL 16.4 (fake)",)]
        elif sql.startswith("SELECT"):
            self._result = [dict(t) for t in self.db.tareas]
        elif sql.startswith("INSERT"):
            tarea = {"id": self.db.next_id, "titulo": params[0],
                     "completada": False, "creada_en": datetime(2026, 11, 22)}
            self.db.next_id += 1
            self.db.tareas.append(tarea)
            self._result = [dict(tarea)]
        elif sql.startswith("UPDATE"):
            self._result = []
            for t in self.db.tareas:
                if t["id"] == params[0]:
                    t["completada"] = not t["completada"]
                    self._result = [dict(t)]
        elif sql.startswith("DELETE"):
            antes = len(self.db.tareas)
            self.db.tareas = [t for t in self.db.tareas if t["id"] != params[0]]
            self.rowcount = antes - len(self.db.tareas)

    def fetchone(self):
        return self._result[0] if self._result else None

    def fetchall(self):
        return self._result


class FakeConn:
    def __init__(self, db):
        self.db = db

    def cursor(self, cursor_factory=None):
        return FakeCursor(self.db)


@pytest.fixture
def client(monkeypatch):
    db = FakeDB()

    @contextmanager
    def fake_get_conn(*args, **kwargs):
        yield FakeConn(db)

    monkeypatch.setattr(app_module, "get_conn", fake_get_conn)
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


# ---------- Configuracion ----------

def test_se_conecta_por_nombre_de_servicio():
    """La app debe apuntar al servicio 'db', nunca a localhost ni a una IP."""
    assert app_module.DB_CONFIG["host"] == "db"


def test_credenciales_vienen_de_variables_de_entorno():
    assert app_module.DB_CONFIG["password"] == os.environ["POSTGRES_PASSWORD"]


# ---------- API ----------

def test_health_reporta_host_db(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["db_host"] == "db"


def test_crear_y_listar_tarea(client):
    r = client.post("/api/tareas", json={"titulo": "Configurar Jenkins"})
    assert r.status_code == 201
    assert r.get_json()["titulo"] == "Configurar Jenkins"

    tareas = client.get("/api/tareas").get_json()
    assert [t["titulo"] for t in tareas] == ["Configurar Jenkins"]


def test_crear_tarea_sin_titulo_es_rechazada(client):
    r = client.post("/api/tareas", json={"titulo": "   "})
    assert r.status_code == 400


def test_alternar_tarea_completada(client):
    client.post("/api/tareas", json={"titulo": "Hacer pruebas"})
    r = client.patch("/api/tareas/1")
    assert r.status_code == 200
    assert r.get_json()["completada"] is True


def test_alternar_tarea_inexistente_da_404(client):
    assert client.patch("/api/tareas/99").status_code == 404


def test_borrar_tarea(client):
    client.post("/api/tareas", json={"titulo": "Temporal"})
    assert client.delete("/api/tareas/1").status_code == 204
    assert client.get("/api/tareas").get_json() == []


def test_borrar_tarea_inexistente_da_404(client):
    assert client.delete("/api/tareas/99").status_code == 404
