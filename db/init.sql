-- Contenedor 2: PostgreSQL
-- Este script se ejecuta automaticamente la PRIMERA vez que se crea el volumen.

CREATE TABLE IF NOT EXISTS tareas (
    id          SERIAL PRIMARY KEY,
    titulo      VARCHAR(200) NOT NULL,
    completada  BOOLEAN      NOT NULL DEFAULT FALSE,
    creada_en   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO tareas (titulo) VALUES
    ('Instalar Docker Desktop'),
    ('Levantar los contenedores con docker compose up');
