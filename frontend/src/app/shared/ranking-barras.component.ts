import { NgFor, NgIf, NgTemplateOutlet } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';

import { IconoComponent, NombreIcono } from './icono.component';
import { RevealDirective } from './reveal.directive';

export interface FilaRanking {
  /** nombre a mostrar (producto o municipio) */
  etiqueta: string;
  /** magnitud cruda, usada solo para calcular el largo de la barra */
  valor: number;
  /** texto ya formateado a la derecha, ej. "18 ofertas" o "$2.400 / kg" */
  display: string;
  icono?: NombreIcono;
}

/**
 * Lista de barras horizontales ranqueadas (top productos, top municipios,
 * precio de referencia…). Sin librería de gráficos: es una barra de progreso
 * por fila, dimensionada contra el máximo del propio listado — mismo espíritu
 * que `app-mapa-casanare`, hecho a mano para no salirse del sistema de diseño.
 */
@Component({
  selector: 'app-ranking-barras',
  standalone: true,
  imports: [NgFor, NgIf, NgTemplateOutlet, IconoComponent, RevealDirective],
  template: `
    <ol class="rk">
      <li *ngFor="let f of items; let i = index; trackBy: trackKey" [appReveal]="i * 45">
        <button *ngIf="clicable; else fila" type="button" class="rk__fila rk__fila--clic"
                (click)="elegir.emit(f.etiqueta)">
          <ng-container *ngTemplateOutlet="contenido; context: { f: f }" />
        </button>
        <ng-template #fila>
          <div class="rk__fila">
            <ng-container *ngTemplateOutlet="contenido; context: { f: f }" />
          </div>
        </ng-template>
      </li>
    </ol>

    <ng-template #contenido let-f="f">
      <app-icono *ngIf="f.icono" [name]="f.icono" [size]="16" class="rk__icono" />
      <span class="rk__etiqueta">{{ f.etiqueta }}</span>
      <span class="rk__barra"><span class="rk__relleno" [style.width.%]="pct(f.valor)"></span></span>
      <span class="rk__valor dato">{{ f.display }}</span>
    </ng-template>
  `,
  styles: [`
    :host { display: block; }
    .rk { list-style: none; margin: 0; padding: 0; display: grid; gap: 0.3rem; }

    .rk__fila {
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr) minmax(70px, 34%) auto;
      align-items: center;
      gap: 0.65rem;
      width: 100%;
      min-height: 38px;
      padding: 0.35rem 0.2rem;
      font-family: var(--sans);
      color: var(--tinta);
      background: transparent;
      border: none;
      border-radius: var(--r);
      text-align: left;
      cursor: default;
    }
    .rk__fila--clic { cursor: pointer; transition: background var(--anim); }
    .rk__fila--clic:hover { background: var(--papel-alt); }
    .rk__fila--clic:hover .rk__etiqueta { color: var(--tierra-hondo); }

    .rk__icono { color: var(--tierra); flex-shrink: 0; }
    .rk__etiqueta {
      font-size: 0.92rem;
      font-weight: 500;
      text-transform: capitalize;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      transition: color var(--anim);
    }

    .rk__barra {
      position: relative;
      height: 7px;
      border-radius: 999px;
      background: var(--papel-alt);
      overflow: hidden;
    }
    .rk__relleno {
      position: absolute;
      inset: 0;
      width: 0;
      border-radius: 999px;
      background: linear-gradient(90deg, var(--oro), var(--tierra));
      transition: width var(--anim-lento);
    }

    .rk__valor {
      font-size: 0.82rem;
      color: var(--humo);
      white-space: nowrap;
      text-align: right;
    }

    @media (max-width: 480px) {
      .rk__fila { grid-template-columns: 18px minmax(0, 1fr) auto; }
      .rk__barra { display: none; }
    }
  `],
})
export class RankingBarrasComponent {
  @Input({ required: true }) items: FilaRanking[] = [];
  /** si true, cada fila es un botón real que emite `elegir` con la etiqueta */
  @Input() clicable = false;
  @Output() elegir = new EventEmitter<string>();

  pct(valor: number): number {
    const max = Math.max(1, ...this.items.map(i => i.valor));
    return Math.max(4, Math.round((valor / max) * 100));
  }

  trackKey(_: number, f: FilaRanking) {
    return f.etiqueta;
  }
}
