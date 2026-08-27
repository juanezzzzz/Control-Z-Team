import { Producto } from './models';

const PESOS = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 0,
});

export function formatoPrecio(valor?: number | null): string {
  if (valor === null || valor === undefined) return 'Precio a convenir';
  return PESOS.format(valor);
}

export function formatoCantidad(p: Producto): string {
  if (p.cantidad === null || p.cantidad === undefined) return '';
  const unidad = p.unidad ? ` ${p.unidad}` : '';
  return `${new Intl.NumberFormat('es-CO').format(p.cantidad)}${unidad}`;
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
