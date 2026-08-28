import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { RespuestaConsulta } from '../../core/models';
import { IconoComponent } from '../../shared/icono.component';
import { ProductoCardComponent } from '../../shared/producto-card.component';
import { RevealDirective } from '../../shared/reveal.directive';

@Component({
  selector: 'app-buscar',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, RouterLink, ProductoCardComponent, RevealDirective, IconoComponent],
  templateUrl: './buscar.component.html',
  styleUrl: './buscar.component.scss',
})
export class BuscarComponent {
  private api = inject(ApiService);

  mensaje = signal('');
  cargando = signal(false);
  error = signal(false);
  respuesta = signal<RespuestaConsulta | null>(null);
  /** eco de lo que se está consultando, para el estado de espera */
  consultaEnCurso = signal('');

  ejemplos = [
    'Busco plátano hartón por Yopal',
    'Necesito leche cerca de Aguazul',
    '50 kilos de yuca en Tauramena',
  ];

  usarEjemplo(texto: string) {
    this.mensaje.set(texto);
    this.consultar();
  }

  consultar() {
    const texto = this.mensaje().trim();
    if (!texto || this.cargando()) return;

    this.cargando.set(true);
    this.error.set(false);
    this.respuesta.set(null);
    this.consultaEnCurso.set(texto);

    this.api
      .consultar(texto)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.cargando.set(false);
        if (res === null) {
          this.error.set(true);
          return;
        }
        this.respuesta.set(res);
      });
  }
}
