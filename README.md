# Lista de Tareas con Docker: dos contenedores comunicados

Proyecto de **Integración Continua** (Entrega 1: Docker · Entrega 2: Jenkins).
Una aplicación web de tareas (To-Do) en **Python/Flask** guarda y lee sus datos de **PostgreSQL**. Cada uno corre en su propio contenedor y los dos se comunican dentro de una red de Docker usando el **nombre del servicio** (`db`). Un servidor **Jenkins**, también en Docker, prueba y construye el proyecto automáticamente con cada push (ver [Integración continua con Jenkins](#integración-continua-con-jenkins)).

## Arquitectura

```
        Navegador / curl
              │  http://localhost:5000
              ▼
┌───────────────────────── red_todo (bridge) ─────────────────────────┐
│                                                                      │
│   ┌──────────────────────┐   host: "db", puerto 5432  ┌───────────┐  │
│   │  app (todo-app)      │ ─────────────────────────▶ │ db        │  │
│   │  Python 3.12 + Flask │ ◀───────────────────────── │ Postgres  │  │
│   │  gunicorn :5000      │      resultados SQL        │ 16.4      │  │
│   └──────────────────────┘                            └─────┬─────┘  │
│                                                             │        │
└─────────────────────────────────────────────────────────────┼────────┘
                                                              ▼
                                                 volumen: datos_postgres
```

| Servicio | Rol | Imagen base | Puerto | Datos |
|----------|-----|-------------|--------|-------|
| `app` | API REST + página web | `python:3.12.7-slim` | 5000 (publicado) | — |
| `db`  | Base de datos | `postgres:16.4-alpine` | 5432 (solo en la red interna) | volumen `datos_postgres` |

## Estructura del repositorio

```
.
├── app/                    # Contenedor 1: aplicación
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── app.py              # API Flask (se conecta a DB_HOST=db)
│   ├── requirements.txt
│   ├── requirements-dev.txt  # pytest (solo para pruebas)
│   ├── tests/test_app.py     # pruebas unitarias
│   └── templates/index.html
├── db/                     # Contenedor 2: base de datos
│   ├── Dockerfile
│   ├── .dockerignore
│   └── init.sql            # crea la tabla "tareas"
├── jenkins/                # Servidor Jenkins (Entrega 2)
│   ├── Dockerfile          # jenkins/jenkins:2.580.2-lts-jdk21 + cliente Docker
│   ├── plugins.txt         # plugins instalados
│   ├── jenkins.yaml        # Configuration as Code: usuario, credencial y job
│   ├── docker-compose.yml
│   └── .env.example
├── ci/
│   ├── docker-compose.ci.yml   # ajustes del compose para correr dentro de Jenkins
│   └── prueba_comunicacion.py  # prueba de integración app -> db
├── Jenkinsfile             # pipeline de Jenkins (pipeline como código)
├── .github/workflows/ci.yml  # pipeline de GitHub Actions
├── docker-compose.yml
├── .env.example            # plantilla de variables (el .env real NO se sube)
└── .gitignore
```

## Requisitos

- Docker Desktop (incluye Docker Compose v2)
- Git

## Cómo levantar el proyecto

```bash
# 1. Clonar el repositorio
git clone <URL-del-repo>
cd <carpeta-del-repo>

# 2. Crear el archivo de variables a partir de la plantilla
#    (en PowerShell: copy .env.example .env)
cp .env.example .env
#    -> editar .env y poner una contraseña propia

# 3. Construir y levantar los dos contenedores
docker compose up --build
```

Abrir **http://localhost:5000** en el navegador.

Comandos útiles:

```bash
docker build -t todo-app:1.0.0 ./app      # construir solo la imagen de la app
docker build -t todo-db:1.0.0 ./db        # construir solo la imagen de la base de datos
docker compose up -d --build              # levantar en segundo plano
docker ps                                 # ver contenedores corriendo
docker network inspect red_todo           # ver la red y los contenedores conectados
docker compose logs -f app                # ver logs de la app
docker compose down                       # apagar (los datos se conservan en el volumen)
docker compose down -v                    # apagar y BORRAR el volumen de datos
```

## Prueba de comunicación (ida y vuelta)

La app se conecta a la base de datos con `DB_HOST=db`, que es el nombre del servicio en `docker-compose.yml`. El DNS interno de Docker resuelve ese nombre. No se usa `localhost` ni una IP fija.

**PowerShell (Windows):**

```powershell
# 1. Verificar conexión app -> db
Invoke-RestMethod http://localhost:5000/health

# 2. GUARDAR un dato
Invoke-RestMethod -Method Post -Uri http://localhost:5000/api/tareas `
  -ContentType "application/json" -Body '{"titulo":"Entregar proyecto Docker"}'

# 3. LEER el dato de vuelta
Invoke-RestMethod http://localhost:5000/api/tareas
```

**Bash / curl:**

```bash
curl http://localhost:5000/health
curl -X POST http://localhost:5000/api/tareas -H "Content-Type: application/json" -d '{"titulo":"Entregar proyecto Docker"}'
curl http://localhost:5000/api/tareas
```

**Comprobar que el nombre `db` se resuelve dentro de la red:**

```bash
docker compose exec app python -c "import socket; print('db ->', socket.gethostbyname('db'))"
```

**Ver el dato directamente en PostgreSQL** (usa el usuario y la base que pusiste en `.env`):

```bash
docker compose exec db psql -U tareas_user -d tareas_db -c "SELECT * FROM tareas;"
```

### Endpoints de la API

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET    | `/` | Página web de tareas |
| GET    | `/health` | Verifica la conexión con la base de datos |
| GET    | `/api/tareas` | Lista las tareas |
| POST   | `/api/tareas` | Crea una tarea `{"titulo": "..."}` |
| PATCH  | `/api/tareas/<id>` | Marca o desmarca una tarea como completada |
| DELETE | `/api/tareas/<id>` | Elimina una tarea |

## Buenas prácticas aplicadas

- Imágenes base **oficiales con versión fija** (nada de `latest`).
- `.dockerignore` en cada servicio.
- Contraseñas solo en `.env` (ignorado por git). En el repo solo está `.env.example`.
- Ningún secreto en el código: todo llega por variables de entorno.
- La app corre con un **usuario sin privilegios** (`appuser`).
- La base de datos **no publica puertos** al host; solo es accesible dentro de `red_todo`.
- `healthcheck` en la base de datos y `depends_on: condition: service_healthy` en la app.
- Servidor de producción **gunicorn** en lugar del servidor de desarrollo de Flask.

## Integración continua con Jenkins

Jenkins corre en su propio contenedor (`jenkins/jenkins:2.580.2-lts-jdk21`) y queda configurado como código con **JCasC**: usuario administrador, credencial de la base de datos y el job `todo-docker-compose`. No aparece el asistente de instalación.

### Levantar Jenkins

```bash
cd jenkins
cp .env.example .env        # en PowerShell: copy .env.example .env  -> cambiar las claves
docker compose up -d --build
docker logs -f jenkins-todo # esperar "Jenkins is fully up and running"
```

Abrir **http://localhost:8080** e ingresar con el usuario y la clave de `jenkins/.env`.

| Elemento | Valor |
|----------|-------|
| Puerto | `8080` (interfaz web) |
| Volumen | `jenkins_home_todo` (jobs, historial, credenciales cifradas) |
| Acceso a Docker | socket `/var/run/docker.sock` del anfitrión (solo laboratorio local) |
| Plugins | Git, GitHub, Pipeline, Docker Pipeline, Credentials Binding, JUnit, Stage View, Graph View, JCasC, Job DSL |
| Credencial | `postgres-password` (Secret text), leída en el pipeline con `withCredentials` |
| Disparo | Poll SCM `H/2 * * * *`: Jenkins revisa GitHub cada ~2 min y ejecuta el pipeline si hay commits nuevos |

### Pipeline (`Jenkinsfile`)

```
Checkout ──▶ Pruebas unitarias ──▶ Build ──▶ Test de integración ──▶ post (limpieza)
             (pytest en un         (docker    (compose up + prueba
              contenedor python     build app  app -> db por nombre
              efímero)              y db)      de servicio)
```

1. **Checkout:** descarga el código desde GitHub.
2. **Pruebas unitarias:** `pytest` dentro de un contenedor `python:3.12.7-slim` efímero; el reporte JUnit se publica en Jenkins.
3. **Build:** construye las imágenes `todo-app` y `todo-db` de la Entrega 1.
4. **Test de integración:** levanta el compose con `ci/docker-compose.ci.yml` (otros nombres de contenedor, red y volumen, y sin puertos publicados, para no chocar con el ambiente de desarrollo) y ejecuta `ci/prueba_comunicacion.py` dentro del contenedor `app`: verifica que `db` se resuelve por DNS interno, que `/health` responde con `db_host = db` y hace un POST + GET real.
5. **post:** siempre apaga los contenedores, borra el volumen y las imágenes de prueba. Si cualquier etapa falla, el build queda en rojo y las etapas siguientes no se ejecutan.

### Correr las pruebas unitarias localmente

```bash
cd app
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Linux/macOS: .venv/bin/pip
.venv/Scripts/python -m pytest -v
```

## Integración continua con GitHub Actions

`.github/workflows/ci.yml` se ejecuta en cada **push** y **pull request**:

1. Construye las dos imágenes con `docker build`.
2. Valida el `docker-compose.yml`.
3. Levanta los servicios con `docker compose up`.
4. Hace la prueba de ida y vuelta (POST + GET) y verifica la resolución DNS de `db`.
5. Apaga todo.
