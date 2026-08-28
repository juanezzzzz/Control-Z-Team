import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { NuevaOferta, Producto, RespuestaConsulta } from './models';

// Cuando el backend está detrás de un túnel ngrok (desarrollo con backend
// local), ngrok intercepta las peticiones GET con una página de aviso
// ("¿confías en este sitio?") salvo que venga este header. Es inofensivo
// contra cualquier otro backend (Render, etc.): simplemente lo ignoran.
const HEADERS = new HttpHeaders({ 'ngrok-skip-browser-warning': 'true' });

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiBase;

  /** GET /api/productos/catalogo — catálogo público de ofertas activas. */
  catalogo(): Observable<Producto[]> {
    return this.http.get<Producto[]>(`${this.base}/api/productos/catalogo`, { headers: HEADERS });
  }

  /** POST /api/sistema/agentes/consulta — búsqueda en lenguaje natural (Agente 3). */
  consultar(mensaje: string): Observable<RespuestaConsulta> {
    return this.http.post<RespuestaConsulta>(
      `${this.base}/api/sistema/agentes/consulta`,
      { mensaje },
      { headers: HEADERS },
    );
  }

  /** POST /api/productos — publica una oferta desde el formulario web. */
  publicar(oferta: NuevaOferta): Observable<Producto> {
    return this.http.post<Producto>(`${this.base}/api/productos`, oferta, { headers: HEADERS });
  }

  // --- Panel de administrador (/admin) — requieren el token del login ---

  /** POST /api/admin/login — usuario/contraseña -> token de sesión. */
  adminLogin(usuario: string, contrasena: string): Observable<{ token: string }> {
    return this.http.post<{ token: string }>(
      `${this.base}/api/admin/login`,
      { usuario, contrasena },
      { headers: HEADERS },
    );
  }

  /** GET /api/admin/productos — todas las ofertas, cualquier estado. */
  adminListar(token: string): Observable<Producto[]> {
    return this.http.get<Producto[]>(`${this.base}/api/admin/productos`, { headers: this.conToken(token) });
  }

  /** PATCH /api/admin/productos/{id}/estado — moderar una oferta. */
  adminCambiarEstado(token: string, id: string, estado: string): Observable<Producto> {
    return this.http.patch<Producto>(
      `${this.base}/api/admin/productos/${id}/estado`,
      { estado },
      { headers: this.conToken(token) },
    );
  }

  /** DELETE /api/admin/productos/{id} — borrado permanente. */
  adminEliminar(token: string, id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/api/admin/productos/${id}`, { headers: this.conToken(token) });
  }

  private conToken(token: string): HttpHeaders {
    return HEADERS.set('Authorization', `Bearer ${token}`);
  }
}
