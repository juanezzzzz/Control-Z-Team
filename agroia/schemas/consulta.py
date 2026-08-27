from typing import Optional
from pydantic import BaseModel

from .producto import ProductoOut


class ConsultaAgente3In(BaseModel):
    """Entrada de POST /api/sistema/agentes/consulta."""

    mensaje: str
    telegram_user_id: Optional[str] = None


class ConsultaAgente3Out(BaseModel):
    respuesta_texto: str
    resultados: list[ProductoOut] = []
