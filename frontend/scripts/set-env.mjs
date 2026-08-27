/**
 * Genera src/environments/environment.production.ts a partir de la variable
 * de entorno API_BASE_URL antes de `ng build`.
 *
 * - En Vercel: define API_BASE_URL en Project Settings → Environment Variables
 *   (p. ej. https://agroia-backend.onrender.com) y este script la inyecta.
 * - En local: si no hay API_BASE_URL, no toca el archivo y `npm run build`
 *   usa el valor que ya esté commiteado.
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const apiBase = (process.env.API_BASE_URL ?? '').trim().replace(/\/+$/, '');

if (!apiBase) {
  console.log('[set-env] API_BASE_URL no definida — se conserva environment.production.ts');
  process.exit(0);
}

const target = resolve(dirname(fileURLToPath(import.meta.url)), '../src/environments/environment.production.ts');

const contents = `/**
 * Generado por scripts/set-env.mjs a partir de API_BASE_URL.
 * No editar a mano: cambia la variable de entorno y vuelve a construir.
 */
export const environment = {
  produccion: true,
  apiBase: '${apiBase}',
};
`;

writeFileSync(target, contents);
console.log(`[set-env] environment.production.ts -> apiBase='${apiBase}'`);
