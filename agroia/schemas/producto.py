from typing import Optional
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
    estado: str = "activo"

    # Estandarizados por el Agente 2. Van en null cuando la unidad no tiene
    # equivalencia fija (bulto, racimo), así que la tarjeta en Angular debe
    # mostrar el precio por unidad base solo si viene.
    municipio: Optional[str] = None
    unidad_base: Optional[str] = None
    cantidad_base: Optional[float] = None
    precio_por_unidad_base: Optional[float] = None


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
