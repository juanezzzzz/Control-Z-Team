import { Component, Input } from '@angular/core';

/**
 * La línea del horizonte: hairline recurrente con una palma llanera posada
 * encima. Es el elemento firma de AgroIA — separa secciones y encabeza el hero.
 * En cada hato del llano el ganado se marca con un hierro propio; aquí la marca
 * de la casa es el horizonte.
 */
@Component({
  selector: 'app-horizonte',
  standalone: true,
  template: `
    <div class="horizonte" [class.horizonte--claro]="claro" role="presentation">
      <svg viewBox="0 0 1200 48" preserveAspectRatio="none" aria-hidden="true">
        <line x1="0" y1="34" x2="1200" y2="34" />
      </svg>
      <svg class="horizonte__palma" viewBox="0 0 40 44" aria-hidden="true">
        <path d="M20 44V20" />
        <path d="M20 20C20 20 12 22 7 15M20 20C20 20 28 22 33 15M20 20C20 20 15 12 18 3M20 20C20 20 25 12 22 3M20 20C20 20 10 16 4 20M20 20c0 0 10-4 16 0" />
      </svg>
    </div>
  `,
  styles: [`
    .horizonte {
      position: relative;
      width: 100%;
      height: 48px;
      color: var(--niebla);
    }
    .horizonte svg { width: 100%; height: 100%; display: block; }
    .horizonte line { stroke: currentColor; stroke-width: 1; vector-effect: non-scaling-stroke; }
    .horizonte__palma {
      position: absolute;
      left: 50%;
      bottom: 0;
      width: 40px;
      height: 44px;
      transform: translateX(-50%);
      color: var(--verde-hoja);
    }
    .horizonte__palma path {
      fill: none;
      stroke: currentColor;
      stroke-width: 1.6;
      stroke-linecap: round;
    }
    .horizonte--claro { color: rgba(251, 250, 245, 0.28); }
    .horizonte--claro .horizonte__palma { color: var(--ocre-sabana); }
  `],
})
export class HorizonteComponent {
  @Input() claro = false;
}
