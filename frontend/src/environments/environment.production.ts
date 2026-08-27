/**
 * Configuración de producción para `ng build`.
 *
 * En Vercel NO se edita a mano: define la variable de entorno `API_BASE_URL`
 * (Project Settings → Environment Variables) y `scripts/set-env.mjs` regenera
 * este archivo en cada build.
 *
 * Fuera de Vercel: reemplaza `apiBase` por la URL pública del backend
 * (Render / Railway / Fly.io), p. ej. https://agroia-backend.onrender.com
 */
export const environment = {
  produccion: true,
  apiBase: 'https://tu-backend-en-produccion.com',
};
