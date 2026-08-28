import { Producto } from './models';
import { NombreIcono } from '../shared/icono.component';

const PESOS = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

export function formatoPrecio(valor?: number | null): string {
  if (valor === null || valor === undefined) return 'A convenir';
  return PESOS.format(valor);
}

/** true cuando el precio es un número (para tratarlo tipográficamente como dato). */
export function hayPrecio(valor?: number | null): boolean {
  return valor !== null && valor !== undefined;
}

export function formatoCantidad(p: Producto): string {
  if (p.cantidad === null || p.cantidad === undefined) return '';
  const unidad = p.unidad ? ` ${p.unidad}` : '';
  return `${new Intl.NumberFormat('es-CO').format(p.cantidad)}${unidad}`;
}

/** Sufijo del precio: «por kg», «por bulto»… Singulariza la unidad. */
export function unidadPrecio(p: Producto): string {
  if (p.precio === null || p.precio === undefined) return '';
  const u = (p.unidad ?? '').trim().toLowerCase();
  if (!u) return '';
  const singular = u
    .replace(/^(kilos?|kg)$/, 'kg')
    .replace(/^libras$/, 'libra')
    .replace(/^arrobas$/, 'arroba')
    .replace(/^bultos$/, 'bulto')
    .replace(/^litros$/, 'litro')
    .replace(/^canastillas$/, 'canastilla')
    .replace(/^unidades$/, 'unidad')
    .replace(/^racimos$/, 'racimo');
  return `por ${singular}`;
}

/** Enlace de contacto: wa.me si parece teléfono, si no un tel:. */
export function enlaceContacto(telefono?: string | null): string | null {
  if (!telefono) return null;
  const limpio = telefono.replace(/[^\d+]/g, '');
  if (limpio.length < 7) return null;
  return `https://wa.me/${limpio.replace(/^\+/, '')}`;
}

/** Inicial para el sello del productor. */
export function inicial(texto?: string | null): string {
  const t = (texto ?? '').trim();
  return t ? t[0].toUpperCase() : '·';
}

/**
 * Elige un glifo del campo a partir del nombre del producto. Se compara palabra
 * por palabra (no subcadenas: "fresco" no debe activar "res").
 */
const GLIFOS: [RegExp, NombreIcono][] = [
  [/^(pl[áa]tano|banano|hart[óo]n|topocho|guineo)/, 'platano'],
  [/^(arroz|paddy)/, 'arroz'],
  [/^(ma[íi]z|mazorca|choclo)/, 'maiz'],
  [/^(yuca|casabe|casava|mandioca)/, 'yuca'],
  [/^(caf[ée]|pergamino)/, 'cafe'],
  [/^(cacao|chocolate)/, 'cacao'],
  [/^(leche|yogur|kumis|cuajada|suero)/, 'leche'],
  [/^(queso|quesillo)/, 'queso'],
  [/^(miel|abejas?|apic|apiario)/, 'miel'],
  [/^(huevos?|gallina)/, 'huevos'],
  [/^(res|reses|ganado|ganader|carne|novillos?|ternera?|brahman|ceb[úu]|vacuno)/, 'res'],
  [/^(pescado|pesca|pez|cachama|bocachico|bagre|s[áa]balo|mojarra|tilapia|cap[ií]taz)/, 'pescado'],
  [/^(panela|ca[ñn]a|melado|melao)/, 'panela'],
  [/^(naranja|lim[óo]n|mandarina|c[íi]trico|toronja|guayaba|mara[ñn][óo]n|lima)/, 'citricos'],
  [/^(tomate|cebolla|ahuyama|auyama|habichuela|pepino|papa|arveja|f[íi]j?ol|fr[íi]j?ol|hortaliza|verdura|piment[óo]n|zanahoria|lechuga|c[íi]lantro)/, 'hortaliza'],
];

export function glifoDeProducto(nombre?: string | null): NombreIcono {
  const palabras = (nombre ?? '').toLowerCase().split(/[\s,./-]+/).filter(Boolean);
  for (const palabra of palabras) {
    for (const [re, glifo] of GLIFOS) if (re.test(palabra)) return glifo;
  }
  return 'hoja';
}
