import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { glifoDeProducto } from '../../core/format';
import { Producto } from '../../core/models';
import { IconoComponent, NombreIcono } from '../../shared/icono.component';
import { ConteoMunicipio, MapaCasanareComponent } from '../../shared/mapa-casanare.component';
import { ProductoCardComponent } from '../../shared/producto-card.component';
import { RevealDirective } from '../../shared/reveal.directive';

type Orden = 'recientes' | 'precio-asc' | 'precio-desc';
type Estado = 'cargando' | 'listo' | 'error';

interface Categoria {
  glifo: NombreIcono;
  etiqueta: string;
  total: number;
}

const NOMBRE_CATEGORIA: Partial<Record<NombreIcono, string>> = {
  platano: 'Plátano', arroz: 'Arroz', maiz: 'Maíz', yuca: 'Yuca', cafe: 'Café',
  cacao: 'Cacao', leche: 'Leche', queso: 'Queso', miel: 'Miel', huevos: 'Huevos',
  res: 'Ganado', pescado: 'Pescado', panela: 'Panela', citricos: 'Cítricos',
  hortaliza: 'Hortalizas', hoja: 'Otros',
};

@Component({
  selector: 'app-catalogo',
  standalone: true,
  imports: [
    NgIf, NgFor, FormsModule, RouterLink,
    ProductoCardComponent, RevealDirective, IconoComponent, MapaCasanareComponent,
  ],
  templateUrl: './catalogo.component.html',
  styleUrl: './catalogo.component.scss',
})
export class CatalogoComponent {
  private api = inject(ApiService);
  private router = inject(Router);
  private ruta = inject(ActivatedRoute);

  estado = signal<Estado>('cargando');
  private ofertas = signal<Producto[]>([]);

  texto = signal('');
  lugar = signal('');
  categoria = signal<NombreIcono | ''>('');
  orden = signal<Orden>('recientes');
  mapaVisible = signal(true);

  conteos = computed<ConteoMunicipio[]>(() =>
    this.ofertas()
      .map(p => ({ nombre: (p.ubicacion ?? '').trim(), total: 1 }))
      .filter(c => !!c.nombre),
  );

  categorias = computed<Categoria[]>(() => {
    const m = new Map<NombreIcono, number>();
    for (const p of this.ofertas()) {
      const g = glifoDeProducto(p.producto);
      m.set(g, (m.get(g) ?? 0) + 1);
    }
    return [...m.entries()]
      .map(([glifo, total]) => ({ glifo, etiqueta: NOMBRE_CATEGORIA[glifo] ?? 'Otros', total }))
      .sort((a, b) => b.total - a.total || a.etiqueta.localeCompare(b.etiqueta, 'es'));
  });

  filtradas = computed(() => {
    const q = this.texto().trim().toLowerCase();
    const l = this.lugar().toLowerCase();
    const cat = this.categoria();

    let lista = this.ofertas().filter(p => {
      const okTexto = !q ||
        p.producto.toLowerCase().includes(q) ||
        (p.ubicacion ?? '').toLowerCase().includes(q);
      const okLugar = !l || (p.ubicacion ?? '').toLowerCase() === l;
      const okCat = !cat || glifoDeProducto(p.producto) === cat;
      return okTexto && okLugar && okCat;
    });

    const alto = Number.POSITIVE_INFINITY;
    switch (this.orden()) {
      case 'precio-asc':
        lista = [...lista].sort((a, b) => (a.precio ?? alto) - (b.precio ?? alto));
        break;
      case 'precio-desc':
        lista = [...lista].sort((a, b) => (b.precio ?? -1) - (a.precio ?? -1));
        break;
    }
    return lista;
  });

  hayFiltros = computed(() =>
    !!this.texto().trim() || !!this.lugar() || !!this.categoria() || this.orden() !== 'recientes');

  constructor() {
    const lugarUrl = this.ruta.snapshot.queryParamMap.get('lugar');
    if (lugarUrl) this.lugar.set(lugarUrl);
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

  elegirLugar(nombre: string) {
    this.lugar.set(nombre);
    this.sincronizarUrl();
  }

  elegirCategoria(g: NombreIcono) {
    this.categoria.update(actual => (actual === g ? '' : g));
  }

  limpiar() {
    this.texto.set('');
    this.lugar.set('');
    this.categoria.set('');
    this.orden.set('recientes');
    this.sincronizarUrl();
  }

  private sincronizarUrl() {
    const lugar = this.lugar();
    this.router.navigate([], {
      relativeTo: this.ruta,
      queryParams: lugar ? { lugar } : {},
      replaceUrl: true,
    });
  }

  alternarMapa() {
    this.mapaVisible.update(v => !v);
  }

  trackById(_: number, p: Producto) { return p.id; }
  retardo(i: number) { return Math.min(i * 50, 300); }
}
