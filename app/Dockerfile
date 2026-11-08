# Contenedor 1: aplicacion To-Do en Flask
# Imagen base oficial con version fija (no "latest")
FROM python:3.12.7-slim

# Evita archivos .pyc y fuerza logs sin buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependencias primero para aprovechar la cache de capas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo de la aplicacion
COPY . .

# Ejecutar como usuario sin privilegios (buena practica de seguridad)
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# Healthcheck: verifica que la app responde y llega a la base de datos
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Comando de inicio con servidor de produccion (gunicorn)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
