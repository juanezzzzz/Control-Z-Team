/** Coincide con ProductoOut del backend (agroia/schemas/producto.py). */
export interface Producto {
  id: string;
  producto: string;
  cantidad?: number | null;
  unidad?: string | null;
  precio?: number | null;
  /** texto libre tal como lo escribió el productor */
  ubicacion?: string | null;
  telefono_contacto?: string | null;
  estado: string;

  // Campos estandarizados por el Agente 2. Vienen en null cuando la unidad no
  // tiene equivalencia fija (bulto, racimo), así que la ficha muestra el precio
  // por unidad base solo si llega.
  /** municipio normalizado; es el que casa con el mapa */
  municipio?: string | null;
  unidad_base?: string | null;
  cantidad_base?: number | null;
  precio_por_unidad_base?: number | null;

  /** fecha de publicación (ISO), para el panel de estadísticas */
  created_at?: string | null;
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
