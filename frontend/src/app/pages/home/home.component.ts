import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { Producto } from '../../core/models';
import { HorizonteComponent } from '../../shared/horizonte.component';
import { ProductoCardComponent } from '../../shared/producto-card.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [NgIf, NgFor, RouterLink, HorizonteComponent, ProductoCardComponent],
  templateUrl: './home.component.html',
  styleUrl: './home.component.scss',
})
export class HomeComponent {
  private api = inject(ApiService);

  private catalogo = signal<Producto[]>([]);
  cargado = signal(false);

  destacados = computed(() => this.catalogo().slice(0, 6));
  totalOfertas = computed(() => this.catalogo().length);
  totalVeredas = computed(() => {
    const set = new Set(
      this.catalogo()
        .map(p => (p.ubicacion ?? '').trim().toLowerCase())
        .filter(Boolean),
    );
    return set.size;
  });

  pasos = [
    {
      titulo: 'El productor manda un mensaje',
      texto:
        'Un campesino le escribe al bot de Telegram —o le manda una nota de voz— algo como «tengo 20 kilos de plátano a 2.000 el kilo por Yopal».',
    },
    {
      titulo: 'La IA ordena la oferta',
      texto:
        'Tres agentes de Claude transcriben el audio, extraen producto, cantidad, precio y vereda, y si falta un dato lo preguntan antes de publicar.',
    },
    {
      titulo: 'Tú la encuentras y contactas',
      texto:
        'La oferta aparece en el catálogo al instante. Buscas en lenguaje natural y hablas directo con quien cosechó. Sin intermediario.',
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
}
