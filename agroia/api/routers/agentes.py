"""POST /api/sistema/agentes/consulta — endpoint interno invocado por el
Agente 3 para buscar productos que coincidan con la intención de un
comprador. Útil también para probar el Agente 3 sin pasar por Telegram
(ej. desde /docs o Postman).
"""
from fastapi import APIRouter, HTTPException

from agroia.agents.agente3_ventas import atender_consulta_comprador
from agroia.schemas import ConsultaAgente3In, ConsultaAgente3Out

router = APIRouter(prefix="/api/sistema/agentes", tags=["agentes"])


@router.post("/consulta", response_model=ConsultaAgente3Out)
def post_consulta_agente3(body: ConsultaAgente3In):
    if not body.mensaje.strip():
        raise HTTPException(status_code=400, detail="El campo 'mensaje' no puede estar vacío.")
    return atender_consulta_comprador(body.mensaje)
