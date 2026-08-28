from typing import Optional
from pydantic import BaseModel


class OfertaExtraida(BaseModel):
    """Salida del Agente 1 (y entrada del Agente 2)."""

    producto: Optional[str] = None
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio: Optional[float] = None
    ubicacion: Optional[str] = None
    # Nombre y contacto del productor. Obligatorios en el flujo de Telegram
    # (ver CAMPOS_OBLIGATORIOS en agente1_recepcion.py); el formulario web
    # los recibe aparte, como campos propios de ProductoIn.
    nombre_productor: Optional[str] = None
    telefono_contacto: Optional[str] = None
    completo: bool = False
    pregunta_faltante: Optional[str] = None
