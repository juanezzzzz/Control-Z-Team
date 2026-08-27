from typing import Optional
from pydantic import BaseModel


class OfertaExtraida(BaseModel):
    """Salida del Agente 1 (y entrada del Agente 2)."""

    producto: Optional[str] = None
    cantidad: Optional[float] = None
    unidad: Optional[str] = None
    precio: Optional[float] = None
    ubicacion: Optional[str] = None
    completo: bool = False
    pregunta_faltante: Optional[str] = None
