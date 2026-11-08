# Contenedor 2: base de datos PostgreSQL
# Imagen base oficial con version fija (no "latest")
FROM postgres:16.4-alpine

# Script de inicializacion: crea la tabla "tareas" la primera vez
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql

EXPOSE 5432
