/** Coincide con ProductoOut del backend (agroia/schemas/producto.py). */
export interface Producto {
  id: string;
  producto: string;
  cantidad?: number | null;
  unidad?: string | null;
  precio?: number | null;
  ubicacion?: string | null;
  telefono_contacto?: string | null;
  estado: string;
}

/** Entrada de POST /api/productos (ProductoIn). */
export interface NuevaOferta {
  producto: string;
  cantidad?: number | null;
  unidad?: string | null;
  precio?: number | null;
  ubicacion: string;
  nombre_productor?: string | null;
  telefono_contacto?: string | null;
}

/** Respuesta de POST /api/sistema/agentes/consulta (ConsultaAgente3Out). */
export interface RespuestaConsulta {
  respuesta_texto: string;
  resultados: Producto[];
}
