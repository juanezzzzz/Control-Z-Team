import { Component, Input, booleanAttribute } from '@angular/core';
import { NgIf } from '@angular/common';

import {
  enlaceContacto, formatoCantidad, formatoPrecio, glifoDeProducto, hayPrecio, unidadPrecio,
} from '../core/format';
import { Producto } from '../core/models';
import { IconoComponent } from './icono.component';

/**
 * Tarjeta de oferta. Jerarquía: producto → precio (el dato que decide) →
 * origen → acción. El glifo del producto marca la esquina como un sello de
 * remisión; el precio manda tipográficamente.
 */
@Component({
  selector: 'app-producto-card',
  standalone: true,
  imports: [NgIf, IconoComponent],
  host: { '[class.destacada]': 'destacada' },
  template: `
    <article class="of">
      <header class="of__cab">
        <span class="of__glifo" aria-hidden="true">
          <app-icono [name]="glifo" [size]="22" />
        </span>
        <span class="of__lugar coord" *ngIf="producto.ubicacion">
          <app-icono name="ubicacion" [size]="12" />{{ producto.ubicacion }}
        </span>
        <span class="of__marca" *ngIf="destacada">Nueva</span>
      </header>

      <h3 class="of__nombre">{{ producto.producto }}</h3>

      <p class="of__precio">
        <span class="of__precio-n" [class.dato]="tienePrecio" [class.sin]="!tienePrecio">{{ precio }}</span>
        <span class="of__precio-u" *ngIf="porUnidad">{{ porUnidad }}</span>
      </p>

      <dl class="of__meta" *ngIf="cantidad">
        <div>
          <dt>Disponible</dt>
          <dd class="dato">{{ cantidad }}</dd>
        </div>
      </dl>

      <footer class="of__pie">
        <a *ngIf="contacto; else sinContacto" class="btn btn--primario of__cta"
           [href]="contacto" target="_blank" rel="noopener"
           [attr.aria-label]="'Escribir por WhatsApp al productor de ' + producto.producto">
          <app-icono name="whatsapp" [size]="16" />
          Escribir al productor
        </a>
        <ng-template #sinContacto>
          <span class="of__espera">
            <app-icono name="reloj" [size]="14" /> Contacto por confirmar
          </span>
        </ng-template>
      </footer>
    </article>
  `,
  styles: [`
    :host { display: block; height: 100%; }

    .of {
      position: relative;
      display: flex;
      flex-direction: column;
      height: 100%;
      padding: var(--s-5);
      background: var(--lienzo);
      border: var(--hair);
      border-radius: var(--r);
      transition: border-color var(--anim), box-shadow var(--anim), transform var(--anim);
    }
    .of:hover {
      border-color: var(--tinta);
      box-shadow: var(--sombra-2);
      transform: translateY(-2px);
    }
    :host(.destacada) .of { border-color: var(--oro-hondo); }

    .of__cab {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      margin-bottom: var(--s-4);
    }
    .of__glifo {
      display: grid;
      place-items: center;
      width: 38px; height: 38px;
      flex-shrink: 0;
      color: var(--tierra);
      background: color-mix(in srgb, var(--tierra) 8%, transparent);
      border-radius: var(--r);
      transition: background var(--anim), color var(--anim);
    }
    .of:hover .of__glifo { background: var(--tierra); color: #FFFFFF; }

    .of__lugar {
      display: inline-flex;
      align-items: center;
      gap: 0.25rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--humo);
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .of__marca {
      margin-left: auto;
      flex-shrink: 0;
      padding: 0.2rem 0.45rem;
      font-family: var(--mono);
      font-size: 0.65rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--tinta);
      background: var(--oro);
      border-radius: 2px;
    }

    .of__nombre {
      margin: 0 0 var(--s-3);
      font-size: 1.3rem;
      line-height: 1.15;
      text-transform: capitalize;
    }

    .of__precio {
      display: flex;
      align-items: baseline;
      gap: 0.35rem;
      margin: 0 0 var(--s-4);
      padding-bottom: var(--s-4);
      border-bottom: var(--hair);
    }
    .of__precio-n {
      font-size: 1.6rem;
      font-weight: 600;
      letter-spacing: -0.03em;
      color: var(--tinta);
    }
    .of__precio-n.sin {
      font-family: var(--sans);
      font-size: 1.05rem;
      font-weight: 500;
      letter-spacing: 0;
      color: var(--humo);
    }
    .of__precio-u { font-size: 0.85rem; color: var(--humo); }

    .of__meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem var(--s-5);
      margin: 0 0 var(--s-5);
    }
    .of__meta dt {
      font-family: var(--mono);
      font-size: 0.65rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--humo);
      margin-bottom: 0.1rem;
    }
    .of__meta dd { margin: 0; font-size: 0.95rem; font-weight: 500; color: var(--carbon); }

    .of__pie { margin-top: auto; }
    .of__cta { width: 100%; }
    .of__espera {
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      min-height: 44px;
      font-size: 0.88rem;
      color: var(--humo);
    }
  `],
})
export class ProductoCardComponent {
  @Input({ required: true }) producto!: Producto;
  /** marca la oferta como recién publicada */
  @Input({ transform: booleanAttribute }) destacada = false;

  get glifo() { return glifoDeProducto(this.producto?.producto); }
  get precio() { return formatoPrecio(this.producto?.precio); }
  get tienePrecio() { return hayPrecio(this.producto?.precio); }
  get porUnidad() { return unidadPrecio(this.producto); }
  get cantidad() { return formatoCantidad(this.producto); }
  get contacto() { return enlaceContacto(this.producto?.telefono_contacto); }
}
