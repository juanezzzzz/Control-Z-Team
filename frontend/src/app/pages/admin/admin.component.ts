import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { NgFor, NgIf } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { catchError, of } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { formatoCantidad, formatoPrecio, lugarDe } from '../../core/format';
import { Producto } from '../../core/models';
import { IconoComponent } from '../../shared/icono.component';

type EstadoCarga = 'inicial' | 'cargando' | 'listo' | 'error';
type FiltroEstado = 'todos' | 'activo' | 'vendido' | 'inactivo';

const TOKEN_KEY = 'agroia_admin_token';

const NOMBRE_ESTADO: Record<string, string> = {
  activo: 'Activo',
  vendido: 'Vendido',
  inactivo: 'Inactivo',
};

/**
 * Panel de administrador (moderar ofertas: cambiar estado, eliminar).
 * Sin enlace en el menú público a propósito — se llega escribiendo /admin.
 * Un solo usuario (ver agroia/core/admin_auth.py), token en sessionStorage
 * (se pierde al cerrar la pestaña, no queda viviendo en el navegador).
 */
@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [NgIf, NgFor, FormsModule, IconoComponent],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent {
  private api = inject(ApiService);

  token = signal<string | null>(this.leerToken());

  // --- login ---
  usuario = signal('');
  contrasena = signal('');
  entrando = signal(false);
  errorLogin = signal<string | null>(null);

  // --- listado ---
  estadoCarga = signal<EstadoCarga>('inicial');
  private productos = signal<Producto[]>([]);
  filtro = signal<FiltroEstado>('todos');
  accionEnCurso = signal<string | null>(null);
  errorAccion = signal<string | null>(null);

  productosFiltrados = computed(() => {
    const f = this.filtro();
    return f === 'todos' ? this.productos() : this.productos().filter(p => p.estado === f);
  });

  conteoPorEstado = computed(() => {
    const c: Record<string, number> = { activo: 0, vendido: 0, inactivo: 0 };
    for (const p of this.productos()) c[p.estado] = (c[p.estado] ?? 0) + 1;
    return c;
  });

  nombreEstado(estado: string): string {
    return NOMBRE_ESTADO[estado] ?? estado;
  }

  lugar(p: Producto): string {
    return lugarDe(p);
  }

  precio(p: Producto): string {
    return formatoPrecio(p.precio);
  }

  cantidad(p: Producto): string {
    return formatoCantidad(p) || '—';
  }

  constructor() {
    if (this.token()) this.cargar();
  }

  login() {
    if (this.entrando()) return;
    const usuario = this.usuario().trim();
    const contrasena = this.contrasena();
    if (!usuario || !contrasena) return;

    this.errorLogin.set(null);
    this.entrando.set(true);

    let statusFallo = 0;
    this.api
      .adminLogin(usuario, contrasena)
      .pipe(catchError((err: HttpErrorResponse) => { statusFallo = err.status; return of(null); }))
      .subscribe(res => {
        this.entrando.set(false);
        if (!res) {
          this.errorLogin.set(
            statusFallo === 429
              ? 'Demasiados intentos fallidos. Espera unos minutos y vuelve a intentar.'
              : 'Usuario o contraseña incorrectos.',
          );
          return;
        }
        this.contrasena.set(''); // no dejarla viva en el signal más de lo necesario
        this.guardarToken(res.token);
        this.cargar();
      });
  }

  cargar() {
    const token = this.token();
    if (!token) return;

    this.estadoCarga.set('cargando');
    let statusFallo = 0;
    this.api
      .adminListar(token)
      .pipe(catchError((err: HttpErrorResponse) => { statusFallo = err.status; return of(null); }))
      .subscribe(data => {
        if (data === null) {
          if (statusFallo === 401) this.cerrarSesion('Tu sesión expiró. Vuelve a iniciar sesión.');
          else this.estadoCarga.set('error');
          return;
        }
        this.productos.set(data);
        this.estadoCarga.set('listo');
      });
  }

  cambiarEstado(p: Producto, estado: string) {
    const token = this.token();
    if (!token || p.estado === estado) return;

    this.errorAccion.set(null);
    this.accionEnCurso.set(p.id);
    this.api
      .adminCambiarEstado(token, p.id, estado)
      .pipe(catchError(() => of(null)))
      .subscribe(actualizado => {
        this.accionEnCurso.set(null);
        if (!actualizado) {
          this.errorAccion.set(`No se pudo actualizar "${p.producto}". Intenta de nuevo.`);
          return;
        }
        this.productos.update(lista => lista.map(x => (x.id === p.id ? actualizado : x)));
      });
  }

  eliminar(p: Producto) {
    const token = this.token();
    if (!token) return;
    if (!confirm(`¿Eliminar definitivamente la oferta de ${p.producto}? Esta acción no se puede deshacer.`)) {
      return;
    }

    this.errorAccion.set(null);
    this.accionEnCurso.set(p.id);
    this.api
      .adminEliminar(token, p.id)
      .pipe(catchError(() => of('error' as const)))
      .subscribe(res => {
        this.accionEnCurso.set(null);
        if (res === 'error') {
          this.errorAccion.set(`No se pudo eliminar "${p.producto}". Intenta de nuevo.`);
          return;
        }
        this.productos.update(lista => lista.filter(x => x.id !== p.id));
      });
  }

  cerrarSesion(mensaje?: string) {
    this.token.set(null);
    this.productos.set([]);
    this.estadoCarga.set('inicial');
    this.filtro.set('todos');
    if (mensaje) this.errorLogin.set(mensaje);
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* almacenamiento no disponible (privado/incógnito) — nada que limpiar */
    }
  }

  trackById(_: number, p: Producto) {
    return p.id;
  }

  private leerToken(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  }

  private guardarToken(token: string) {
    this.token.set(token);
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* almacenamiento no disponible — la sesión no sobrevive un refresh, pero funciona en la pestaña actual */
    }
  }
}
