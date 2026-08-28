import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { formatoPrecio, glifoDeProducto, lugarDe } from '../../core/format';
import { Producto } from '../../core/models';
import { IconoComponent } from '../../shared/icono.component';
import { ConteoMunicipio, MapaCasanareComponent } from '../../shared/mapa-casanare.component';
import { FilaRanking, RankingBarrasComponent } from '../../shared/ranking-barras.component';
import { PuntoTendencia, TendenciaChartComponent } from '../../shared/tendencia-chart.component';
import { RevealDirective } from '../../shared/reveal.directive';

type Estado = 'cargando' | 'listo' | 'error';

const DIAS_TENDENCIA = 14;
const MAX_FILAS = 8;

@Component({
  selector: 'app-panel',
  standalone: true,
  imports: [
    NgIf, NgFor, RouterLink,
    IconoComponent, RevealDirective, MapaCasanareComponent,
    RankingBarrasComponent, TendenciaChartComponent,
  ],
  templateUrl: './panel.component.html',
  styleUrl: './panel.component.scss',
})
export class PanelComponent {
  private api = inject(ApiService);
  private router = inject(Router);

  estado = signal<Estado>('cargando');
  private ofertas = signal<Producto[]>([]);

  totalOfertas = computed(() => this.ofertas().length);

  totalMunicipios = computed(() => {
    const s = new Set(this.ofertas().map(p => lugarDe(p).toLowerCase()).filter(Boolean));
    return s.size;
  });

  totalProductos = computed(() => {
    const s = new Set(this.ofertas().map(p => p.producto.trim().toLowerCase()).filter(Boolean));
    return s.size;
  });

  /** teléfonos distintos entre las ofertas activas: proxy de productores únicos */
  totalProductores = computed(() => {
    const s = new Set(
      this.ofertas().map(p => (p.telefono_contacto ?? '').replace(/\D/g, '')).filter(Boolean),
    );
    return s.size;
  });

  conteosMunicipio = computed<ConteoMunicipio[]>(() =>
    this.ofertas().map(p => ({ nombre: lugarDe(p), total: 1 })).filter(c => !!c.nombre),
  );

  topProductos = computed<FilaRanking[]>(() => this.ranking(
    this.ofertas().map(p => p.producto.trim().toLowerCase()).filter(Boolean),
    nombre => glifoDeProducto(nombre),
  ));

  topMunicipios = computed<FilaRanking[]>(() => this.ranking(
    this.ofertas().map(p => lugarDe(p)).filter(Boolean),
    () => 'ubicacion',
  ));

  /** promedio de precio_por_unidad_base agrupado por producto — solo entra lo
   * que el Agente 2 pudo estandarizar (bultos y racimos quedan fuera). */
  precioReferencia = computed<FilaRanking[]>(() => {
    const grupos = new Map<string, { suma: number; n: number; unidad: string }>();
    for (const p of this.ofertas()) {
      if (p.precio_por_unidad_base == null || !p.unidad_base) continue;
      const key = p.producto.trim().toLowerCase();
      if (!key) continue;
      const g = grupos.get(key) ?? { suma: 0, n: 0, unidad: p.unidad_base };
      g.suma += p.precio_por_unidad_base;
      g.n += 1;
      grupos.set(key, g);
    }
    return [...grupos.entries()]
      .sort((a, b) => b[1].n - a[1].n || b[1].suma / b[1].n - a[1].suma / a[1].n)
      .slice(0, 6)
      .map(([nombre, g]) => {
        const promedio = g.suma / g.n;
        return {
          etiqueta: nombre,
          valor: promedio,
          display: `${formatoPrecio(promedio)} / ${g.unidad}`,
          icono: glifoDeProducto(nombre),
        };
      });
  });

  /** ofertas publicadas por día, últimos 14 días (buckets en cero incluidos) */
  tendencia = computed<PuntoTendencia[]>(() => {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);

    const cubos = new Map<string, number>();
    const orden: string[] = [];
    for (let i = DIAS_TENDENCIA - 1; i >= 0; i--) {
      const d = new Date(hoy);
      d.setDate(d.getDate() - i);
      const clave = d.toISOString().slice(0, 10);
      cubos.set(clave, 0);
      orden.push(clave);
    }

    for (const p of this.ofertas()) {
      if (!p.created_at) continue;
      const clave = p.created_at.slice(0, 10);
      if (cubos.has(clave)) cubos.set(clave, (cubos.get(clave) ?? 0) + 1);
    }

    const formato = new Intl.DateTimeFormat('es-CO', { day: '2-digit', month: 'short' });
    return orden.map(clave => ({
      etiqueta: formato.format(new Date(`${clave}T12:00:00`)).replace('.', ''),
      valor: cubos.get(clave) ?? 0,
    }));
  });

  ofertasUltimos14 = computed(() => this.tendencia().reduce((a, p) => a + p.valor, 0));

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

  /** Un clic en el mapa o en el ranking de municipios lleva al catálogo ya filtrado. */
  irAMunicipio(nombre: string) {
    if (!nombre) return;
    this.router.navigate(['/catalogo'], { queryParams: { lugar: nombre } });
  }

  /** Cuenta ocurrencias, ordena de mayor a menor y arma las filas del ranking. */
  private ranking(nombres: string[], icono: (nombre: string) => FilaRanking['icono']): FilaRanking[] {
    const m = new Map<string, number>();
    for (const n of nombres) m.set(n, (m.get(n) ?? 0) + 1);
    return [...m.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, MAX_FILAS)
      .map(([nombre, total]) => ({
        etiqueta: nombre,
        valor: total,
        display: `${total} ${total === 1 ? 'oferta' : 'ofertas'}`,
        icono: icono(nombre),
      }));
  }
}
