import { Component, Input } from '@angular/core';
import { NgIf } from '@angular/common';

import { enlaceContacto, formatoCantidad, formatoPrecio, inicial } from '../core/format';
import { Producto } from '../core/models';

/**
 * Ficha sellada: cada oferta se presenta como un tiquete con el sello del
 * productor (un hierro con su inicial), el dato en monoespaciada y el contacto
 * directo. Sin intermediario entre la ficha y la llamada.
 */
@Component({
  selector: 'app-producto-card',
  standalone: true,
  imports: [NgIf],
  template: `
    <article class="ficha">
      <div class="ficha__sello" aria-hidden="true">{{ ini }}</div>

      <div class="ficha__cuerpo">
        <p class="ficha__lugar dato" *ngIf="producto.ubicacion">{{ producto.ubicacion }}</p>
        <h3 class="ficha__nombre">{{ producto.producto }}</h3>

        <dl class="ficha__datos">
          <div>
            <dt>Precio</dt>
            <dd class="dato">{{ precio }}</dd>
          </div>
          <div *ngIf="cantidad">
            <dt>Disponible</dt>
            <dd class="dato">{{ cantidad }}</dd>
          </div>
        </dl>
      </div>

      <div class="ficha__pie">
        <a *ngIf="contacto; else sinContacto" class="btn btn--ocre" [href]="contacto" target="_blank" rel="noopener">
          Contactar al productor
        </a>
        <ng-template #sinContacto>
          <span class="ficha__nota">Contacto por definir</span>
        </ng-template>
      </div>
    </article>
  `,
  styles: [`
    .ficha {
      position: relative;
      display: flex;
      flex-direction: column;
      background: var(--hueso);
      border: var(--borde);
      border-radius: var(--radio);
      padding: 1.4rem 1.4rem 1.2rem;
      transition: transform var(--transicion), box-shadow var(--transicion), border-color var(--transicion);
    }
    .ficha:hover {
      transform: translateY(-3px);
      box-shadow: var(--sombra);
      border-color: var(--verde-hoja);
    }
    /* muesca de tiquete */
    .ficha::before,
    .ficha::after {
      content: '';
      position: absolute;
      top: 72px;
      width: 14px;
      height: 14px;
      background: var(--cielo-llano);
      border: var(--borde);
      border-radius: 50%;
    }
    .ficha::before { left: -8px; }
    .ficha::after { right: -8px; }

    .ficha__sello {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      font-family: var(--display);
      font-weight: 700;
      font-size: 1.3rem;
      color: var(--verde-galeria);
      border: 2px solid var(--ocre-sabana);
      border-radius: 50%;
      margin-bottom: 1rem;
    }
    .ficha__lugar {
      font-size: 0.72rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--ocre-hondo);
      margin: 0 0 0.35rem;
    }
    .ficha__nombre {
      font-size: 1.35rem;
      text-transform: capitalize;
      margin: 0 0 1rem;
    }
    .ficha__datos {
      display: flex;
      gap: 1.5rem;
      margin: 0 0 1.3rem;
      padding-top: 0.9rem;
      border-top: 1px dashed var(--niebla);
    }
    .ficha__datos dt {
      font-size: 0.68rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--musgo);
      margin-bottom: 0.15rem;
    }
    .ficha__datos dd { margin: 0; font-size: 1rem; font-weight: 600; color: var(--noche); }
    .ficha__pie { margin-top: auto; }
    .ficha__pie .btn { width: 100%; justify-content: center; }
    .ficha__nota { font-size: 0.85rem; color: var(--musgo); }
  `],
})
export class ProductoCardComponent {
  @Input({ required: true }) producto!: Producto;

  get ini() { return inicial(this.producto?.producto); }
  get precio() { return formatoPrecio(this.producto?.precio); }
  get cantidad() { return formatoCantidad(this.producto); }
  get contacto() { return enlaceContacto(this.producto?.telefono_contacto); }
}
