#!/bin/sh
set -e

# El healthcheck de "mysql" (mysqladmin ping) a veces responde justo antes de
# que el servidor acepte conexiones de aplicación; se reintenta la migración
# unas cuantas veces en vez de depender de que el contenedor se reinicie solo.
intentos=10
intento=1
migrado=0
while [ "$intento" -le "$intentos" ]; do
  if alembic upgrade head; then
    migrado=1
    break
  fi
  echo "No se pudo conectar a la base de datos (intento $intento/$intentos); reintentando en 3s..."
  intento=$((intento + 1))
  sleep 3
done

if [ "$migrado" -ne 1 ]; then
  echo "No se pudo aplicar la migración tras $intentos intentos."
  exit 1
fi

exec uvicorn gestor_tareas.main:app --host 0.0.0.0 --port 8000
