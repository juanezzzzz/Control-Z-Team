# AgroIA Casanare — Frontend

SPA en Angular 18 (standalone components) para el mercado campesino de Casanare.

| Ruta         | Módulo                | Endpoint del backend                    |
|--------------|-----------------------|-----------------------------------------|
| `/`          | Home / landing        | `GET /api/productos/catalogo`            |
| `/catalogo`  | Catálogo + filtros    | `GET /api/productos/catalogo`            |
| `/buscar`    | Búsqueda con IA        | `POST /api/sistema/agentes/consulta`     |
| `/publicar`  | Publicar una oferta    | `POST /api/productos`                    |

## Desarrollo local

```bash
npm install
npm start          # http://localhost:4200
```

Levanta el backend en paralelo (`uvicorn agroia.main:app --reload --port 8000`).
La URL del backend para desarrollo está en `src/environments/environment.ts`
(`apiBase`, por defecto `http://localhost:8000`).

El backend debe permitir el origen del frontend: en su `.env`,
`CORS_ALLOW_ORIGINS=http://localhost:4200` (o `*` solo en local).

## Build de producción

```bash
npm run build      # -> dist/frontend/browser/
```

## Despliegue en Vercel

1. **Importa el repo** en Vercel. En *Project Settings*:
   - **Root Directory**: `frontend`
   - Framework, build command y output directory ya vienen definidos en
     `vercel.json` (`framework: angular`, salida `dist/frontend/browser`,
     rewrite SPA a `index.html`).
2. **Variable de entorno** (*Settings → Environment Variables*):
   - `API_BASE_URL` = URL pública del backend, p. ej.
     `https://agroia-backend.onrender.com` (sin barra final).
   - `scripts/set-env.mjs` la inyecta en `environment.production.ts` en cada build.
3. **Deploy.** Vercel corre `npm run vercel-build`.
4. **CORS en el backend**: añade el dominio de Vercel a `CORS_ALLOW_ORIGINS`,
   p. ej. `https://agroia.vercel.app` (y el de preview si lo usas).

### Alternativa sin CORS (proxy)

Si prefieres que el navegador no llame al backend directamente, deja
`API_BASE_URL` vacía (el frontend usará rutas relativas `/api/...`) y añade a
`vercel.json` un rewrite del API hacia el backend **antes** del rewrite SPA:

```json
{ "source": "/api/(.*)", "destination": "https://TU-BACKEND/api/$1" }
```

Así todo es same-origin y no hace falta tocar el CORS del backend.
