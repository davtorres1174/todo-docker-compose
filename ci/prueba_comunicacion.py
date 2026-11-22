"""
Prueba de integracion: se ejecuta DENTRO del contenedor "app" desde Jenkins.

  docker compose ... exec -T app python - < ci/prueba_comunicacion.py

Verifica que la aplicacion se comunica con PostgreSQL usando el NOMBRE DEL
SERVICIO ("db") y hace una operacion real de ida y vuelta (guardar y leer).
Si cualquier verificacion falla, termina con codigo 1 y el build queda en rojo.
"""
import json
import socket
import sys
import time
import urllib.request

BASE = "http://localhost:5000"


def pedir(metodo, ruta, datos=None):
    cuerpo = json.dumps(datos).encode() if datos is not None else None
    req = urllib.request.Request(BASE + ruta, data=cuerpo, method=metodo,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read() or b"null")


def verificar(condicion, mensaje):
    if not condicion:
        print("FALLO:", mensaje)
        sys.exit(1)
    print("OK   :", mensaje)


# 0. Esperar a que la app responda
for intento in range(30):
    try:
        estado, salud = pedir("GET", "/health")
        break
    except Exception as exc:  # la app o la base de datos aun no estan listas
        time.sleep(2)
else:
    print("FALLO: la aplicacion no respondio en 60 segundos")
    sys.exit(1)

# 1. El nombre del servicio "db" se resuelve por el DNS interno de Docker
ip_db = socket.gethostbyname("db")
verificar(not ip_db.startswith("127."), f"el nombre 'db' se resuelve a {ip_db} (red interna de Docker)")

# 2. La app llega a PostgreSQL por el nombre del servicio
verificar(estado == 200 and salud["status"] == "ok", "GET /health responde ok")
verificar(salud["db_host"] == "db", "la app usa db_host = 'db' (no localhost ni IP fija)")
print("       ", salud["db_version"])

# 3. Ida: guardar un dato
titulo = f"Prueba Jenkins {int(time.time())}"
estado, creada = pedir("POST", "/api/tareas", {"titulo": titulo})
verificar(estado == 201, f"POST /api/tareas guarda la tarea id={creada['id']}")

# 4. Vuelta: leer el dato desde PostgreSQL
estado, tareas = pedir("GET", "/api/tareas")
verificar(any(t["titulo"] == titulo for t in tareas), "GET /api/tareas devuelve la tarea guardada")

print("PRUEBA DE COMUNICACION APP -> DB: EXITOSA")
