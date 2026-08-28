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

/**
 * Lugar de la oferta. El Agente 2 normaliza el municipio; `ubicacion` es el
 * texto libre del productor y queda como respaldo para filas antiguas.
 */
export function lugarDe(p: Producto): string {
  return (p.municipio ?? '').trim() || (p.ubicacion ?? '').trim();
}

/**
 * Precio por unidad base cuando el Agente 2 pudo estandarizar la unidad.
 * Devuelve '' si no vino (bulto, racimo… no tienen equivalencia fija) o si
 * coincide con la unidad que ya se muestra, para no repetir el mismo dato.
 */
export function precioBase(p: Producto): string {
  const v = p.precio_por_unidad_base;
  if (v === null || v === undefined || !p.unidad_base) return '';
  const misma = (p.unidad ?? '').trim().toLowerCase() === p.unidad_base.trim().toLowerCase();
  if (misma) return '';
  return `${PESOS.format(v)} por ${p.unidad_base}`;
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

/** Nombre legible de cada categoría (glifo), para chips y gráficos. Única
 * fuente: la usan tanto el catálogo como el panel de estadísticas. */
export const NOMBRE_CATEGORIA: Partial<Record<NombreIcono, string>> = {
  platano: 'Plátano', arroz: 'Arroz', maiz: 'Maíz', yuca: 'Yuca', cafe: 'Café',
  cacao: 'Cacao', leche: 'Leche', queso: 'Queso', miel: 'Miel', huevos: 'Huevos',
  res: 'Ganado', pescado: 'Pescado', panela: 'Panela', citricos: 'Cítricos',
  hortaliza: 'Hortalizas', hoja: 'Otros',
};
