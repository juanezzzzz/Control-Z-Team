FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agroia ./agroia

EXPOSE 8000
# Forma shell (no exec) a propósito: así se expande $PORT. Render (y la
# mayoría de PaaS) asignan el puerto dinámicamente por esa variable; sin
# esto el contenedor escucha en 8000 mientras el proxy manda tráfico al
# puerto que asignó la plataforma, y el healthcheck nunca responde.
CMD uvicorn agroia.main:app --host 0.0.0.0 --port ${PORT:-8000}
