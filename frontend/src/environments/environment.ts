/**
 * URL base del backend FastAPI (main.py).
 * En local: `uvicorn agroia.main:app --reload --port 8000`.
 * En despliegue (Render / Railway / Fly.io) reemplaza por la URL pública.
 */
export const environment = {
  produccion: false,
  apiBase: 'http://localhost:8000',
};
