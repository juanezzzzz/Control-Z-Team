from typing import Optional
from pydantic import BaseModel


class OfertaExtraida(BaseModel):
    """Salida del Agente 1 (y entrada del Agente 2)."""

    producto: Optional[str] = None
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio: Optional[float] = None
    # Unidad a la que se refiere el PRECIO, cuando no es la misma de la
    # cantidad: "2 toneladas a 1500 el kilo" -> unidad="tonelada",
    # unidad_precio="kg". El Agente 2 convierte; sin esto tomaría los $1.500
    # como precio por tonelada y publicaría un precio 1000 veces menor.
    unidad_precio: Optional[str] = None
    ubicacion: Optional[str] = None
    # Nombre y contacto del productor. Obligatorios en el flujo de Telegram
    # (ver CAMPOS_OBLIGATORIOS en agente1_recepcion.py); el formulario web
    # los recibe aparte, como campos propios de ProductoIn.
    nombre_productor: Optional[str] = None
    telefono_contacto: Optional[str] = None
    # Opcional: dirección del local o finca donde el comprador puede ir a
    # comprar en persona. Nunca bloquea la publicación — muchos campesinos
    # venden desde la finca y no tienen un local con dirección.
    direccion_local: Optional[str] = None
    completo: bool = False
    pregunta_faltante: Optional[str] = None
