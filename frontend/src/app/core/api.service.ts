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
}
