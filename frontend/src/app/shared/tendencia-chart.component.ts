import { NgFor, NgIf } from '@angular/common';
import { Component, Input } from '@angular/core';

export interface PuntoTendencia {
  /** etiqueta corta del eje X, ej. "12 ago" */
  etiqueta: string;
  valor: number;
}

interface PuntoGeo {
  x: number;
  y: number;
  etiqueta: string;
  valor: number;
}

const W = 640;
const H = 220;
const PAD_ARRIBA = 16;
const PAD_ABAJO = 30;

/**
 * Serie de tiempo en SVG (área + línea), a mano — mismo criterio que
 * `app-mapa-casanare`: nada de librería de gráficos, geometría calculada
 * contra el propio máximo de la serie y coloreada con las variables del
 * sistema de diseño, no colores fijos.
 */
@Component({
  selector: 'app-tendencia-chart',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <figure class="tc">
      <svg [attr.viewBox]="viewBox" preserveAspectRatio="none" aria-hidden="true" focusable="false">
        <defs>
          <linearGradient id="tc-relleno" x1="0" y1="0" x2="0" y2="1">
            <stop class="tc__grad-i" offset="0%" />
            <stop class="tc__grad-f" offset="100%" />
          </linearGradient>
        </defs>

        <g class="tc__guias">
          <line *ngFor="let y of lineasGuia" x1="0" [attr.x2]="ancho" [attr.y1]="y" [attr.y2]="y" />
        </g>

        <path class="tc__area" [attr.d]="areaPath" fill="url(#tc-relleno)" />
        <path class="tc__linea" [attr.d]="lineaPath" fill="none" />

        <circle *ngFor="let p of geometria; let i = index" class="tc__punto"
                [class.tc__punto--ultimo]="i === geometria.length - 1"
                [attr.cx]="p.x" [attr.cy]="p.y" [attr.r]="i === geometria.length - 1 ? 4.5 : 2.5">
          <title>{{ p.etiqueta }} · {{ p.valor }} {{ p.valor === 1 ? 'oferta' : 'ofertas' }}</title>
        </circle>
      </svg>

      <div class="tc__eje" aria-hidden="true">
        <span *ngFor="let e of etiquetasEje" [style.left.%]="e.pct">{{ e.etiqueta }}</span>
      </div>

      <p class="tc__vacio coord" *ngIf="sinDatos">Aún no hay suficiente actividad para mostrar una tendencia.</p>
    </figure>
  `,
  styles: [`
    :host { display: block; }
    .tc { margin: 0; position: relative; }
    .tc svg { width: 100%; height: auto; display: block; overflow: visible; }

    .tc__guias line { stroke: var(--niebla-alt); stroke-width: 1; opacity: 0.7; }

    .tc__grad-i { stop-color: var(--tierra); stop-opacity: 0.26; }
    .tc__grad-f { stop-color: var(--tierra); stop-opacity: 0; }

    .tc__linea { stroke: var(--tierra); stroke-width: 2.5; stroke-linejoin: round; stroke-linecap: round; }
    .tc__punto { fill: var(--lienzo); stroke: var(--tierra); stroke-width: 2; }
    .tc__punto--ultimo { fill: var(--tierra); stroke: var(--lienzo); stroke-width: 2.5; }

    .tc__eje { position: relative; height: 1rem; margin-top: 0.4rem; }
    .tc__eje span {
      position: absolute;
      top: 0;
      transform: translateX(-50%);
      font-family: var(--mono);
      font-size: 0.68rem;
      color: var(--humo);
      white-space: nowrap;
    }
    .tc__eje span:first-child { transform: translateX(0); }
    .tc__eje span:last-child { transform: translateX(-100%); }

    .tc__vacio {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 0 1rem;
      text-align: center;
      background: color-mix(in srgb, var(--lienzo) 82%, transparent);
    }
  `],
})
export class TendenciaChartComponent {
  @Input({ required: true }) puntos: PuntoTendencia[] = [];

  readonly viewBox = `0 0 ${W} ${H}`;
  readonly ancho = W;

  get sinDatos(): boolean {
    return !this.puntos?.length || this.puntos.every(p => p.valor === 0);
  }

  get geometria(): PuntoGeo[] {
    const datos = this.puntos ?? [];
    const n = datos.length;
    if (!n) return [];
    const max = Math.max(1, ...datos.map(p => p.valor));
    const innerH = H - PAD_ARRIBA - PAD_ABAJO;
    return datos.map((p, i) => ({
      x: n === 1 ? W / 2 : (i * W) / (n - 1),
      y: PAD_ARRIBA + innerH - (p.valor / max) * innerH,
      etiqueta: p.etiqueta,
      valor: p.valor,
    }));
  }

  get lineaPath(): string {
    return this.geometria.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
  }

  get areaPath(): string {
    const g = this.geometria;
    if (!g.length) return '';
    const base = H - PAD_ABAJO;
    const linea = g.map(p => `L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    return `M ${g[0].x.toFixed(1)} ${base} ${linea} L ${g[g.length - 1].x.toFixed(1)} ${base} Z`;
  }

  get lineasGuia(): number[] {
    const base = H - PAD_ABAJO;
    const innerH = H - PAD_ARRIBA - PAD_ABAJO;
    return [0, 0.5, 1].map(f => base - f * innerH);
  }

  /** Máximo 6 etiquetas en el eje X, repartidas a distancia pareja (siempre
   * incluye la primera y la última). Un paso fijo con la última forzada
   * aparte puede dejar dos etiquetas casi pegadas si no cae justo en el
   * paso; repartir por posición relativa evita ese amontonamiento. */
  get etiquetasEje(): { etiqueta: string; pct: number }[] {
    const datos = this.puntos ?? [];
    const n = datos.length;
    if (!n) return [];
    const maxEtiquetas = Math.min(6, n);
    const indices = new Set<number>();
    for (let i = 0; i < maxEtiquetas; i++) {
      indices.add(maxEtiquetas === 1 ? 0 : Math.round((i * (n - 1)) / (maxEtiquetas - 1)));
    }
    return [...indices].sort((a, b) => a - b).map(i => ({
      etiqueta: datos[i].etiqueta,
      pct: n === 1 ? 50 : (i / (n - 1)) * 100,
    }));
  }
}
