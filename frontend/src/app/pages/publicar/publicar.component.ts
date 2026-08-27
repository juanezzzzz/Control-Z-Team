import { Component, inject, signal } from '@angular/core';
import { NgIf } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { NuevaOferta, Producto } from '../../core/models';
import { HorizonteComponent } from '../../shared/horizonte.component';

@Component({
  selector: 'app-publicar',
  standalone: true,
  imports: [NgIf, FormsModule, RouterLink, HorizonteComponent],
  templateUrl: './publicar.component.html',
  styleUrl: './publicar.component.scss',
})
export class PublicarComponent {
  private api = inject(ApiService);

  modelo: NuevaOferta = {
    producto: '',
    cantidad: null,
    unidad: '',
    precio: null,
    ubicacion: '',
    nombre_productor: '',
    telefono_contacto: '',
  };

  unidades = ['kg', 'libras', 'arrobas', 'bultos', 'litros', 'canastillas', 'unidades', 'racimos'];

  enviando = signal(false);
  error = signal<string | null>(null);
  publicada = signal<Producto | null>(null);

  enviar(form: NgForm) {
    if (form.invalid || this.enviando()) {
      form.control.markAllAsTouched();
      return;
    }
    this.enviando.set(true);
    this.error.set(null);

    const payload: NuevaOferta = {
      ...this.modelo,
      producto: this.modelo.producto.trim(),
      ubicacion: this.modelo.ubicacion.trim(),
      unidad: this.modelo.unidad || null,
      nombre_productor: this.modelo.nombre_productor?.trim() || null,
      telefono_contacto: this.modelo.telefono_contacto?.trim() || null,
    };

    this.api
      .publicar(payload)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.enviando.set(false);
        if (res === null) {
          this.error.set('No se pudo publicar la oferta. Revisa la conexión con el backend e inténtalo de nuevo.');
          return;
        }
        this.publicada.set(res);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
  }

  otra() {
    this.modelo = {
      producto: '', cantidad: null, unidad: '', precio: null,
      ubicacion: '', nombre_productor: '', telefono_contacto: '',
    };
    this.publicada.set(null);
    this.error.set(null);
  }
}
