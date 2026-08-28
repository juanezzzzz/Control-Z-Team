import {
  AfterViewInit,
  Component,
  DestroyRef,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule, NgForm } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { MUNICIPIOS_GEO } from '../../core/casanare-mapa.data';
import { NuevaOferta, Producto } from '../../core/models';
import { IconoComponent } from '../../shared/icono.component';
import { ProductoCardComponent } from '../../shared/producto-card.component';

@Component({
  selector: 'app-publicar',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, RouterLink, ProductoCardComponent, IconoComponent],
  templateUrl: './publicar.component.html',
  styleUrl: './publicar.component.scss',
})
export class PublicarComponent implements AfterViewInit {
  private api = inject(ApiService);
  private destroyRef = inject(DestroyRef);

  @ViewChild('refForm') refForm?: NgForm;

  modelo: NuevaOferta = this.vacio();

  /** signal espejo del modelo, para que la vista previa reaccione al tecleo */
  private tick = signal(0);

  unidades = ['kg', 'libras', 'arrobas', 'bultos', 'litros', 'canastillas', 'unidades', 'racimos'];
  municipios = MUNICIPIOS_GEO.map(m => m.name).sort((a, b) => a.localeCompare(b, 'es'));

  enviando = signal(false);
  error = signal<string | null>(null);
  publicada = signal<Producto | null>(null);

  /** ficha de ejemplo que refleja lo que el productor va escribiendo */
  vistaPrevia = computed<Producto>(() => {
    this.tick();
    const m = this.modelo;
    return {
      id: 'previa',
      producto: m.producto?.trim() || 'Tu producto',
      cantidad: m.cantidad ?? null,
      unidad: m.unidad || null,
      precio: m.precio ?? null,
      ubicacion: m.ubicacion?.trim() || 'Tu municipio',
      telefono_contacto: m.telefono_contacto?.trim() || null,
      direccion_local: m.direccion_local?.trim() || null,
      estado: 'activo',
    };
  });

  /** La vista previa se refresca con cada cambio del formulario, sin acoplar campo a campo. */
  ngAfterViewInit() {
    this.refForm?.form.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.tick.update(v => v + 1));
  }

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
      direccion_local: this.modelo.direccion_local?.trim() || null,
    };

    this.api
      .publicar(payload)
      .pipe(catchError(() => of(null)))
      .subscribe(res => {
        this.enviando.set(false);
        if (res === null) {
          this.error.set('No se pudo publicar la oferta. Revisa la conexión e inténtalo de nuevo.');
          return;
        }
        this.publicada.set(res);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
  }

  otra() {
    this.modelo = this.vacio();
    this.tick.update(v => v + 1);
    this.publicada.set(null);
    this.error.set(null);
  }

  private vacio(): NuevaOferta {
    return {
      producto: '', cantidad: null, unidad: '', precio: null,
      ubicacion: '', nombre_productor: '', telefono_contacto: '', direccion_local: '',
    };
  }
}
