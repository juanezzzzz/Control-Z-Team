import { Component, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { RespuestaConsulta } from '../../core/models';
import { ProductoCardComponent } from '../../shared/producto-card.component';

@Component({
  selector: 'app-buscar',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, ProductoCardComponent],
  templateUrl: './buscar.component.html',
  styleUrl: './buscar.component.scss',
})
export class BuscarComponent {
  private api = inject(ApiService);

  mensaje = signal('');
  cargando = signal(false);
  error = signal(false);
  respuesta = signal<RespuestaConsulta | null>(null);

  ejemplos = [
    'Busco plátano hartón por Yopal',
    'Necesito leche cerca de Aguazul',
    'Quiero comprar yuca en Tauramena',
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

    this.api
      .consultar(texto)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.cargando.set(false);
        if (res === null) {
          this.error.set(true);
          this.respuesta.set(null);
          return;
        }
        this.respuesta.set(res);
      });
  }
}
