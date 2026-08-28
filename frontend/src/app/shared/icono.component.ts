import { Component, Input, inject } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

/**
 * Iconos en SVG en línea (sin dependencias). Dos familias:
 *  - de interfaz: ubicación, teléfono, whatsapp, buscar, flecha, check, equis, brote…
 *  - del campo: glifos de producto en el mismo trazo de línea (plátano, arroz,
 *    café, leche, miel, huevos, res, pescado, hoja…). El glifo se elige por
 *    palabra clave del nombre del producto (ver `glifoDeProducto` en core/format).
 *
 * Trazo heredado de `currentColor`; tamaño por `[size]` (px) o `1em` por defecto.
 */
export type NombreIcono =
  | 'ubicacion' | 'telefono' | 'whatsapp' | 'buscar' | 'flecha' | 'check'
  | 'equis' | 'brote' | 'filtro' | 'menu' | 'reloj' | 'chat'
  | 'platano' | 'arroz' | 'maiz' | 'yuca' | 'cafe' | 'cacao' | 'leche'
  | 'queso' | 'miel' | 'huevos' | 'res' | 'pescado' | 'panela' | 'citricos'
  | 'hortaliza' | 'hoja';

const P: Record<NombreIcono, string> = {
  // --- interfaz (geometría estilo Lucide, MIT) ---
  ubicacion: '<path d="M20 10c0 4.4-5.6 9.8-7.4 11.5a.9.9 0 0 1-1.2 0C9.6 19.8 4 14.4 4 10a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/>',
  telefono: '<path d="M15.5 21A13.5 13.5 0 0 1 3 8.5 3 3 0 0 1 6 5.5h2L9.5 9 7.8 10.6a11 11 0 0 0 5.6 5.6L15 14.5 18.5 16v2a3 3 0 0 1-3 3Z"/>',
  whatsapp: '<path d="M4.5 20 5.8 16A8 8 0 1 1 9 19.2Z"/><path d="M9 10c.4 2 2 3.6 4 4"/>',
  chat: '<path d="M20 15a3 3 0 0 1-3 3H8l-4 3V6a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3Z"/>',
  buscar: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  flecha: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  equis: '<path d="M18 6 6 18M6 6l12 12"/>',
  filtro: '<path d="M3 5h18l-7 8v6l-4 2v-8L3 5Z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  reloj: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>',
  brote: '<path d="M7 21h10"/><path d="M12 21v-8"/><path d="M12 13c-3 .3-5-.6-6-2-.9-1.3-1-3.2-1-5 2.4-.2 4.3.2 5.6 1.2C11.8 8.4 12 10.5 12 13Z"/><path d="M12 11c.2-2.6.9-4.4 2.2-5.4C15.6 4.4 17.6 4 20 4c-.1 2.8-.6 4.8-1.8 6C17 11 14.9 11.3 12 11Z"/>',
  // --- del campo (trazo propio) ---
  platano: '<path d="M4 12c1.4 5.2 5.4 8 10.5 8C19 20 21 15 21 10c0-1-1.4-1.4-2-.5-1.4 2.4-4 4-7.5 4-3 0-5-1.4-5-4 0-1-1.8-1.2-2.3.2Z"/>',
  arroz: '<path d="M12 21V9"/><path d="M12 13c-2.6 0-4.4-1.8-4.4-4.6C10.2 8.4 12 10.2 12 13Z"/><path d="M12 13c2.6 0 4.4-1.8 4.4-4.6C13.8 8.4 12 10.2 12 13Z"/><path d="M12 9c-2 0-3.4-1.4-3.4-3.6C10.6 5.4 12 6.8 12 9Z"/><path d="M12 9c2 0 3.4-1.4 3.4-3.6C13.4 5.4 12 6.8 12 9Z"/>',
  maiz: '<path d="M12 21c-3-1-4-4-4-8s1-8 4-9c3 1 4 5 4 9s-1 7-4 8Z"/><path d="M12 4c1-2 3-2 5-1-1 2-3 3-5 3"/><path d="M9.5 8h.01M13.5 8h.01M9.5 12h.01M13.5 12h.01M10.5 16h.01M13 16h.01"/>',
  yuca: '<path d="M9.4 4.5c-1 4-1 8 .6 11.8 1.4 3.3 1.9 4.6 1.4 6.2 2 .3 3.6-1 3.6-3 0-1.5-.6-2.8-.6-5.7s1-6.3 0-9.3c-1.6-1.2-4-1.2-6.6 0Z"/><path d="M10 4c-1-1.2-2.4-1.8-4.2-1.6M14 4c1-1 2.6-1.4 4.2-1"/>',
  cafe: '<path d="M7 9h9l-.8 8.5A2.5 2.5 0 0 1 12.7 20h-2.4a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M16 10h1.5a2.5 2.5 0 0 1 0 5H15"/><path d="M9 6c0-1 .8-2 2-2M13 6c0-1 .8-2 2-2"/>',
  cacao: '<path d="M12 4c4 0 7 3.6 7 8s-3 8-7 8-7-3.6-7-8 3-8 7-8Z"/><path d="M12 5v14M8.6 6.6c1 1.6 1.4 3.5 1.4 5.4s-.4 3.8-1.4 5.4M15.4 6.6c-1 1.6-1.4 3.5-1.4 5.4s.4 3.8 1.4 5.4"/>',
  leche: '<path d="M8 8V4h8v4l1.5 3v9a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-9Z"/><path d="M8 8h8M9 15h6v4H9z"/>',
  queso: '<path d="M3 16 20 8v6a2 2 0 0 1-2 2Z"/><path d="M3 16 20 8"/><circle cx="8" cy="13.5" r="1"/><circle cx="13" cy="12" r="1"/>',
  miel: '<path d="M8 9h8v10a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2Z"/><path d="M9 9V6h6v3M8 13h8"/><path d="M18 4c0 1.4-1 2.5-1 2.5S16 5.4 16 4a1 1 0 0 1 2 0Z"/>',
  huevos: '<path d="M9.5 21c-2.8 0-4.5-2.4-4.5-5.4C5 12 7 8 9.5 8s4.5 4 4.5 7.6C14 18.6 12.3 21 9.5 21Z"/><path d="M16.5 15c-1.8 0-3-1.6-3-3.6C13.5 9 15 6 16.5 6s3 3 3 5.4c0 2-1.2 3.6-3 3.6Z"/>',
  res: '<path d="M6 6C4 6 3 8 4 10M18 6c2 0 3 2 2 4"/><path d="M4.5 9c0-3 3.4-5 7.5-5s7.5 2 7.5 5c0 5-3.4 9-7.5 9S4.5 14 4.5 9Z"/><path d="M9.5 12h.01M14.5 12h.01M10 16c1.2.9 2.8.9 4 0"/>',
  pescado: '<path d="M3 12c3-3.5 7-5.3 11-5.3l-2 5.3 2 5.3C10 17.3 6 15.5 3 12Z"/><path d="M14 6.7c2.4.4 4 1.9 4.6 4.1l2.9-2.3v7l-2.9-2.3c-.6 2.2-2.2 3.7-4.6 4.1"/><path d="M7 11h.5"/>',
  panela: '<path d="M12 21V4"/><path d="M12 4c-.6-1.6-2-2.4-3.5-2M12 4c.6-1.6 2-2.4 3.5-2"/><path d="M9 8h6M9 12h6M9 16h6"/>',
  citricos: '<circle cx="12" cy="13" r="7"/><path d="M12 6c.5-2 2-3 4.5-3M12 13l5-4M12 13v7M12 13l6 3.5M12 13l-6 3.5"/>',
  hortaliza: '<path d="M12 21c-3.5 0-6-2.8-6-6.5S8.5 8 12 8s6 2.8 6 6.5S15.5 21 12 21Z"/><path d="M12 8V4M12 4c-1.4 0-2.5-1.1-2.5-2.5M12 4c1.4 0 2.5-1.1 2.5-2.5"/>',
  hoja: '<path d="M11 20A7 7 0 0 1 4 13C4 7 9 4 20 3c-1 11-4 16-9 17Z"/><path d="M4 13c4.5-1 8-3 10-6"/>',
};

@Component({
  selector: 'app-icono',
  standalone: true,
  template: `<span class="icono" [style.width]="px" [style.height]="px" [innerHTML]="svg"></span>`,
  styles: [`
    :host { display: inline-flex; line-height: 0; }
    .icono { display: inline-flex; }
  `],
})
export class IconoComponent {
  private sanitizer = inject(DomSanitizer);

  @Input({ required: true }) set name(n: NombreIcono) {
    const body = P[n] ?? P['hoja'];
    this._svg = this.sanitizer.bypassSecurityTrustHtml(
      `<svg width="100%" height="100%" viewBox="0 0 24 24" fill="none" stroke="currentColor" ` +
      `stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" ` +
      `style="display:block" aria-hidden="true">${body}</svg>`,
    );
  }

  @Input() size?: number;
  private _svg!: SafeHtml;

  get px() { return this.size ? `${this.size}px` : '1em'; }
  get svg() { return this._svg; }
}
