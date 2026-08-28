from typing import Any, Optional
from pydantic import BaseModel


class ProductoOut(BaseModel):
    """Forma pública de un producto — la que consume el frontend Angular."""

    id: str
    producto: str
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio: Optional[float] = None
    ubicacion: Optional[str] = None
    telefono_contacto: Optional[str] = None
    # Dirección del local/finca para ir a comprar en persona. Opcional.
    direccion_local: Optional[str] = None
    estado: str = "activo"

    # Estandarizados por el Agente 2. Van en null cuando la unidad no tiene
    # equivalencia fija (bulto, racimo), así que la tarjeta en Angular debe
    # mostrar el precio por unidad base solo si viene.
    municipio: Optional[str] = None
    unidad_base: Optional[str] = None
    cantidad_base: Optional[float] = None
    precio_por_unidad_base: Optional[float] = None

    # Para el panel de estadísticas del frontend (actividad reciente).
    created_at: Optional[str] = None


class ProductoIn(BaseModel):
    """Entrada de POST /api/productos: alta directa de una oferta desde el
    formulario web del productor (sin pasar por Telegram). El flujo por
    Telegram sigue existiendo en paralelo."""

    producto: str
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio: Optional[float] = None
    ubicacion: str
    nombre_productor: Optional[str] = None
    telefono_contacto: Optional[str] = None
    direccion_local: Optional[str] = None


def a_producto_out(registro: dict[str, Any]) -> ProductoOut:
    """Mapea una fila cruda de Supabase a `ProductoOut`. Única fuente: la usan
    el catálogo público, el Agente 3 (resultados de búsqueda) y el panel de
    administrador — antes cada uno tenía su propia copia y había que
    recordar actualizar las tres si se agregaba un campo."""
    return ProductoOut(
        id=str(registro["id"]),
        producto=registro["producto"],
        cantidad=registro.get("cantidad"),
        unidad=registro.get("unidad"),
        precio=registro.get("precio"),
        ubicacion=registro.get("ubicacion"),
        telefono_contacto=registro.get("telefono_contacto"),
        direccion_local=registro.get("direccion_local"),
        estado=registro.get("estado", "activo"),
        municipio=registro.get("municipio"),
        unidad_base=registro.get("unidad_base"),
        cantidad_base=registro.get("cantidad_base"),
        precio_por_unidad_base=registro.get("precio_por_unidad_base"),
        created_at=registro.get("created_at"),
    )
