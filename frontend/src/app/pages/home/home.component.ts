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

  /**
   * Dos rutas, no tres agentes: el visitante llega vendiendo o comprando, y el
   * mismo bot lo enruta según lo que escriba. «Agente 1/2/3» es nomenclatura
   * interna de la arquitectura y no le dice nada a quien entra.
   */
  rutas: {
    icono: NombreIcono;
    rotulo: string;
    titulo: string;
    texto: string;
    ejemplo: string;
    foto: string;
    alt: string;
    pie: string;
    enlace: string;
    cta: string;
  }[] = [
    {
      icono: 'brote',
      rotulo: 'Tengo cosecha',
      titulo: 'Lo dices y queda publicada',
      texto:
        'Le hablas al bot de Telegram como le hablarías a un vecino — por texto o nota de voz. Si falta algo (el precio, el municipio, tu número) te lo pregunta, y cuando está completa la publica.',
      ejemplo: 'Tengo 20 kilos de plátano a 2.000 el kilo por Yopal',
      foto: 'campesino-cafetero',
      alt: 'Campesino colombiano con sombrero y costal, esperando el transporte',
      pie: 'Productor colombiano · Hernan Vanegas, CC BY-SA 4.0',
      enlace: '/publicar',
      cta: 'Publicar sin Telegram',
    },
    {
      icono: 'buscar',
      rotulo: 'Estoy comprando',
      titulo: 'Preguntas y te responde con ofertas',
      texto:
        'Escribes lo que necesitas en tus palabras. El sistema entiende producto y zona, busca en el catálogo y te devuelve lo que hay, con el número del productor para escribirle directo.',
      ejemplo: 'Busco 50 kilos de plátano cerca de Yopal',
      foto: 'frutas-mercado',
      alt: 'Puesto de mercado campesino con plátano, papaya, limón y guayaba en canastillas',
      pie: 'Mercado campesino, Colombia · momentcaptured1, CC BY 2.0',
      enlace: '/buscar',
      cta: 'Buscar en la web',
    },
  ];

  /** Lo que efectivamente se comercia en el departamento. */
  cultivos: { foto: string; alt: string; nombre: string; nota: string; credito: string }[] = [
    {
      foto: 'arroz-llanos',
      alt: 'Cultivo de arroz verde bajo el cielo del llano en Maní, Casanare',
      nombre: 'Arroz',
      nota: 'Maní, Casanare',
      credito: 'Anvar2420, CC BY-SA 4.0',
    },
    {
      foto: 'caucho-villanueva',
      alt: 'Vista aérea de cultivos de caucho en Villanueva, Casanare',
      nombre: 'Caucho',
      nota: 'Villanueva, Casanare',
      credito: 'CarlosE Duarte, CC BY 3.0',
    },
    {
      foto: 'cacao-secando',
      alt: 'Granos de cacao secándose al sol sobre una plataforma de madera',
      nombre: 'Cacao',
      nota: 'Secado al sol',
      credito: 'pipeafcr, CC BY-SA 3.0',
    },
    {
      foto: 'llanuras-orocue',
      alt: 'Llanuras y esteros de Orocué, Casanare, vistos desde el aire',
      nombre: 'Sabana',
      nota: 'Orocué, Casanare',
      credito: 'CarlosE Duarte, CC BY 3.0',
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
