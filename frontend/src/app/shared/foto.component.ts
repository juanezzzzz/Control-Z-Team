import { booleanAttribute, Component, Input } from '@angular/core';

/**
 * `<app-foto>` — imagen de Casanare con WebP + JPG de respaldo, carga diferida,
 * relación de aspecto fija (sin saltos de layout) y un fondo de marca mientras
 * carga. Los archivos viven en `public/img/casanare/` (créditos en CREDITS.md).
 */
@Component({
  selector: 'app-foto',
  standalone: true,
  host: { '[class.llena]': 'cover' },
  template: `
    <picture class="foto" [class.foto--cover]="cover" [style.aspect-ratio]="cover ? null : ratio">
      <source [srcset]="'/img/casanare/' + nombre + '.webp'" type="image/webp" />
      <img [src]="'/img/casanare/' + nombre + '.jpg'" [alt]="alt"
           loading="lazy" decoding="async" [style.object-position]="foco" />
    </picture>
  `,
  styles: [`
    :host { display: block; }
    :host(.llena) { height: 100%; }
    .foto {
      display: block;
      width: 100%;
      overflow: hidden;
      background: var(--papel-alt);
    }
    .foto--cover { height: 100%; }
    .foto img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }
  `],
})
export class FotoComponent {
  /** nombre de archivo sin extensión, p. ej. "amanecer-esteros" */
  @Input({ required: true }) nombre!: string;
  @Input({ required: true }) alt!: string;
  /** relación de aspecto CSS, p. ej. "4 / 3" o "16 / 9" */
  @Input() ratio = '4 / 3';
  /** object-position del recorte */
  @Input() foco = 'center';
  /** llena el alto del contenedor en vez de usar una relación de aspecto */
  @Input({ transform: booleanAttribute }) cover = false;
}
