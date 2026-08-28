import { NgFor, NgIf } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  Output,
  computed,
  signal,
} from '@angular/core';

import {
  CASANARE_OUTLINE,
  MAPA_VIEWBOX,
  MUNICIPIOS_GEO,
  MunicipioGeo,
} from '../core/casanare-mapa.data';

export interface ConteoMunicipio {
  /** nombre del municipio tal como lo escribe el productor */
  nombre: string;
  total: number;
}

interface Pieza extends MunicipioGeo {
  total: number;
  intensidad: number;
  seleccionado: boolean;
}

/** Normaliza para comparar «Yopal», «yopal », «YOPAL» y «Maní»/«Mani». */
function clave(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

/**
 * Mapa de Casanare por municipios. No es decoración: cada municipio se pinta
 * según cuántas ofertas activas tiene y al pulsarlo filtra el catálogo.
 * Geometría del DANE (MGN 2018) simplificada; ver core/casanare-mapa.data.ts.
 */
@Component({
  selector: 'app-mapa-casanare',
  standalone: true,
  imports: [NgFor, NgIf],
  template: `
    <figure class="mapa">
      <svg [attr.viewBox]="viewBox" aria-hidden="true" focusable="false">
        <!-- retícula cartográfica -->
        <defs>
          <pattern id="mapa-grilla" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M40 0H0V40" fill="none" stroke="currentColor" stroke-width="0.5" opacity="0.25" />
          </pattern>
        </defs>
        <rect class="mapa__fondo" width="100%" height="100%" fill="url(#mapa-grilla)" />

        <g class="mapa__municipios">
          <path *ngFor="let m of piezas(); trackBy: trackCode"
                [attr.d]="m.d"
                class="mapa__mun"
                [class.tiene]="m.total > 0"
                [class.activo]="m.seleccionado"
                [class.resaltado]="sobre()?.code === m.code"
                [style.--n]="m.intensidad"
                (click)="elegir(m)"
                (mouseenter)="sobre.set(m)"
                (mouseleave)="sobre.set(null)" />
        </g>

        <path class="mapa__borde" [attr.d]="outline" />

        <g class="mapa__pines">
          <g *ngFor="let m of conOfertas(); trackBy: trackCode"
             [attr.transform]="'translate(' + m.cx + ',' + m.cy + ')'" aria-hidden="true">
            <circle class="mapa__pin" [attr.r]="radio(m)" [class.activo]="m.seleccionado" />
            <text class="mapa__pin-n" [attr.y]="radio(m) * 0.34">{{ m.total }}</text>
          </g>
        </g>
      </svg>

      <figcaption class="mapa__pie">
        <span class="mapa__leyenda">
          <span class="mapa__muestra"></span>
          <span class="coord">Menos · más ofertas</span>
        </span>
        <span class="mapa__hover dato" aria-hidden="true">
          {{ sobre() ? etiqueta(sobre()!) : (seleccion ? seleccion : 'Casanare · 19 municipios') }}
        </span>
      </figcaption>

      <!-- El SVG es la vista; esta lista es el mando. Son botones reales, con
           foco y nombre accesible, porque Chrome no dispara ningún evento de
           foco sobre un <path> aunque lleve tabindex. Además deja leer los
           nombres exactos, que en el mapa se apiñan al occidente. -->
      <ul class="mapa__lista" *ngIf="conOfertas().length">
        <li *ngFor="let m of conOfertas(); trackBy: trackCode">
          <button type="button" class="mapa__chip"
                  [class.activo]="m.seleccionado"
                  [attr.aria-pressed]="m.seleccionado"
                  [attr.aria-label]="etiqueta(m)"
                  (click)="elegir(m)"
                  (mouseenter)="sobre.set(m)"
                  (mouseleave)="sobre.set(null)"
                  (focus)="sobre.set(m)"
                  (blur)="sobre.set(null)">
            <span aria-hidden="true">{{ m.name }}</span>
            <span class="mapa__chip-n dato" aria-hidden="true">{{ m.total }}</span>
          </button>
        </li>
      </ul>
    </figure>
  `,
  styles: [`
    :host { display: block; }
    .mapa { margin: 0; }
    .mapa svg {
      width: 100%;
      height: auto;
      display: block;
      color: var(--niebla-alt);
      overflow: visible;
    }
    .mapa__fondo { color: var(--niebla-alt); }

    .mapa__mun {
      fill: var(--lienzo);
      stroke: var(--niebla-alt);
      stroke-width: 1;
      vector-effect: non-scaling-stroke;
      transition: fill var(--anim), stroke var(--anim);
    }
    .mapa__mun.tiene {
      /* --n: 0..1 -> del oro pálido a la tierra */
      fill: color-mix(in srgb, var(--oro) calc(22% + var(--n, 0) * 55%), var(--lienzo));
      cursor: pointer;
    }
    .mapa__mun.tiene:hover {
      fill: color-mix(in srgb, var(--tierra) calc(30% + var(--n, 0) * 45%), var(--lienzo));
      stroke: var(--tinta);
    }
    /* Foco de teclado. Chrome no hace coincidir :focus en un <path> con
       tabindex, así que la clase la pone el componente. El indicador engrosa y
       tiñe el propio contorno: un rectángulo sobre una forma irregular no
       diría cuál municipio está enfocado. */
    .mapa__mun.tiene.resaltado {
      fill: color-mix(in srgb, var(--tierra) calc(30% + var(--n, 0) * 45%), var(--lienzo));
      stroke: var(--rio);
      stroke-width: 3;
    }
    .mapa__mun.activo {
      fill: var(--tierra);
      stroke: var(--tinta);
      stroke-width: 1.5;
    }

    .mapa__borde {
      fill: none;
      stroke: var(--tinta);
      stroke-width: 1.5;
      stroke-linejoin: round;
      vector-effect: non-scaling-stroke;
      opacity: 0.55;
      pointer-events: none;
    }

    .mapa__pines { pointer-events: none; }
    .mapa__pin {
      fill: var(--tinta);
      stroke: var(--papel);
      stroke-width: 4;
      transition: fill var(--anim);
    }
    .mapa__pin.activo { fill: var(--tierra-hondo); }
    .mapa__pin-n {
      fill: var(--papel);
      font-family: var(--mono);
      font-size: 30px;
      font-weight: 600;
      text-anchor: middle;
    }

    .mapa__pie {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 0.5rem 1rem;
      margin-top: 0.85rem;
      padding-top: 0.7rem;
      border-top: var(--hair);
    }
    .mapa__leyenda { display: inline-flex; align-items: center; gap: 0.5rem; }
    .mapa__muestra {
      width: 44px; height: 8px;
      border: 1px solid var(--niebla-alt);
      border-radius: 1px;
      background: linear-gradient(90deg,
        color-mix(in srgb, var(--oro) 22%, var(--lienzo)),
        var(--tierra));
    }
    .mapa__hover { font-size: 0.78rem; color: var(--carbon); }

    .mapa__lista {
      list-style: none;
      margin: 0.85rem 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }
    .mapa__chip {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      min-height: 32px;
      padding: 0.3rem 0.65rem;
      font-family: var(--sans);
      font-size: 0.84rem;
      color: var(--carbon);
      background: transparent;
      border: 1px solid var(--niebla-alt);
      border-radius: 999px;
      cursor: pointer;
      transition: border-color var(--anim), background var(--anim), color var(--anim);
    }
    .mapa__chip:hover { border-color: var(--tinta); color: var(--tinta); }
    .mapa__chip.activo {
      background: var(--tierra);
      border-color: var(--tierra);
      color: #FFFFFF;
    }
    .mapa__chip-n { font-size: 0.78rem; opacity: 0.72; }
  `],
})
export class MapaCasanareComponent {
  /** conteos por municipio, tal como vienen del catálogo */
  @Input({ required: true }) set conteos(v: ConteoMunicipio[]) {
    const mapa = new Map<string, number>();
    for (const c of v ?? []) {
      const k = clave(c.nombre);
      mapa.set(k, (mapa.get(k) ?? 0) + c.total);
    }
    this._conteos.set(mapa);
  }

  /** municipio seleccionado (nombre); vacío = sin filtro */
  @Input() seleccion = '';

  @Output() seleccionar = new EventEmitter<string>();

  viewBox = MAPA_VIEWBOX;
  outline = CASANARE_OUTLINE;
  /** municipio señalado desde el mapa o desde la lista (hover o foco) */
  sobre = signal<Pieza | null>(null);

  private _conteos = signal(new Map<string, number>());

  private max = computed(() => Math.max(1, ...[...this._conteos().values()]));

  piezas = computed<Pieza[]>(() => {
    const c = this._conteos();
    const sel = clave(this.seleccion ?? '');
    const max = this.max();
    return MUNICIPIOS_GEO.map(m => {
      const total = c.get(clave(m.name)) ?? 0;
      return {
        ...m,
        total,
        intensidad: total ? Math.round((total / max) * 100) / 100 : 0,
        seleccionado: !!sel && clave(m.name) === sel,
      };
    });
  });

  conOfertas = computed(() => this.piezas().filter(m => m.total > 0));
  totalOfertas = computed(() => this.conOfertas().reduce((a, m) => a + m.total, 0));
  conActividad = computed(() => this.conOfertas().length);

  /** Radio en unidades del viewBox (1000 de ancho), para que lea a cualquier tamaño. */
  radio(m: Pieza) {
    return 26 + Math.round(m.intensidad * 10);
  }

  etiqueta(m: Pieza) {
    return `${m.name} · ${m.total} ${m.total === 1 ? 'oferta' : 'ofertas'}`;
  }

  elegir(m: Pieza) {
    if (!m.total) return;
    this.seleccionar.emit(m.seleccionado ? '' : m.name);
  }

  trackCode(_: number, m: MunicipioGeo) {
    return m.code;
  }
}
