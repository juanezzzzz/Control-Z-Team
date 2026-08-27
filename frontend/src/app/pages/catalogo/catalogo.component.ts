import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { Producto } from '../../core/models';
import { ProductoCardComponent } from '../../shared/producto-card.component';

type Orden = 'recientes' | 'precio-asc' | 'precio-desc';
type Estado = 'cargando' | 'listo' | 'error';

@Component({
  selector: 'app-catalogo',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, RouterLink, ProductoCardComponent],
  templateUrl: './catalogo.component.html',
  styleUrl: './catalogo.component.scss',
})
export class CatalogoComponent {
  private api = inject(ApiService);

  estado = signal<Estado>('cargando');
  private ofertas = signal<Producto[]>([]);

  texto = signal('');
  ubicacion = signal('');
  orden = signal<Orden>('recientes');

  ubicaciones = computed(() => {
    const set = new Map<string, string>();
    for (const p of this.ofertas()) {
      const u = (p.ubicacion ?? '').trim();
      if (u) set.set(u.toLowerCase(), u);
    }
    return [...set.values()].sort((a, b) => a.localeCompare(b, 'es'));
  });

  filtradas = computed(() => {
    const q = this.texto().trim().toLowerCase();
    const u = this.ubicacion().toLowerCase();
    let lista = this.ofertas().filter(p => {
      const coincideTexto = !q || p.producto.toLowerCase().includes(q);
      const coincideUbic = !u || (p.ubicacion ?? '').toLowerCase() === u;
      return coincideTexto && coincideUbic;
    });

    const sinPrecio = Number.POSITIVE_INFINITY;
    switch (this.orden()) {
      case 'precio-asc':
        lista = [...lista].sort((a, b) => (a.precio ?? sinPrecio) - (b.precio ?? sinPrecio));
        break;
      case 'precio-desc':
        lista = [...lista].sort((a, b) => (b.precio ?? -1) - (a.precio ?? -1));
        break;
    }
    return lista;
  });

  hayFiltros = computed(() => !!this.texto().trim() || !!this.ubicacion() || this.orden() !== 'recientes');

  constructor() {
    this.cargar();
  }

  cargar() {
    this.estado.set('cargando');
    this.api
      .catalogo()
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data === null) {
          this.estado.set('error');
          return;
        }
        this.ofertas.set(data);
        this.estado.set('listo');
      });
  }

  limpiarFiltros() {
    this.texto.set('');
    this.ubicacion.set('');
    this.orden.set('recientes');
  }
}
