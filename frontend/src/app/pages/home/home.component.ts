import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { lugarDe } from '../../core/format';
import { Producto } from '../../core/models';
import { FotoComponent } from '../../shared/foto.component';
import { IconoComponent, NombreIcono } from '../../shared/icono.component';
import { ConteoMunicipio, MapaCasanareComponent } from '../../shared/mapa-casanare.component';
import { ProductoCardComponent } from '../../shared/producto-card.component';
import { RevealDirective } from '../../shared/reveal.directive';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    NgIf, NgFor, RouterLink,
    ProductoCardComponent, RevealDirective, IconoComponent, FotoComponent, MapaCasanareComponent,
  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent {
  private api = inject(ApiService);
  private router = inject(Router);

  private catalogo = signal<Producto[]>([]);
  cargado = signal(false);

  destacados = computed(() => this.catalogo().slice(0, 6));
  totalOfertas = computed(() => this.catalogo().length);

  conteos = computed<ConteoMunicipio[]>(() =>
    this.catalogo()
      .map(p => ({ nombre: lugarDe(p), total: 1 }))
      .filter(c => !!c.nombre),
  );

  totalMunicipios = computed(() => {
    const s = new Set(this.catalogo().map(p => lugarDe(p).toLowerCase()).filter(Boolean));
    return s.size;
  });

  /** productos distintos, para el resumen del hero */
  totalProductos = computed(() => {
    const s = new Set(this.catalogo().map(p => p.producto.trim().toLowerCase()).filter(Boolean));
    return s.size;
  });

  pasos: { icono: NombreIcono; rotulo: string; titulo: string; texto: string }[] = [
    {
      icono: 'chat',
      rotulo: 'Agente 1',
      titulo: 'Manda un mensaje de voz',
      texto:
        'El productor le habla al bot de Telegram como le hablaría a un vecino: «tengo 20 kilos de plátano a 2.000 el kilo por Yopal». Sin app que instalar, sin formularios.',
    },
    {
      icono: 'brote',
      rotulo: 'Agente 2',
      titulo: 'La IA arma la oferta',
      texto:
        'Transcribe el audio, saca producto, cantidad, precio y vereda, y si algo falta lo pregunta antes de publicar. Nadie transcribe a mano.',
    },
    {
      icono: 'ubicacion',
      rotulo: 'Agente 3',
      titulo: 'El comprador la encuentra',
      texto:
        'La oferta entra al mapa al instante. El comprador busca en lenguaje natural, filtra por municipio y escribe directo por WhatsApp.',
    },
  ];

  constructor() {
    this.api
      .catalogo()
      .pipe(catchError(() => of([] as Producto[])))
      .subscribe(data => {
        this.catalogo.set(data);
        this.cargado.set(true);
      });
  }

  /** Un clic en el mapa lleva al catálogo ya filtrado por ese municipio. */
  irAMunicipio(nombre: string) {
    if (!nombre) return;
    this.router.navigate(['/catalogo'], { queryParams: { lugar: nombre } });
  }
}
