"""Agente 1: Recepción y Extracción de Datos (Productor).

Flujo (según el documento de arquitectura, sección 3):
 1. Si el mensaje es audio, ya llega transcrito a texto (ver
    agroia/integrations/speech_to_text.py).
 2. Extrae producto, cantidad, precio, ubicación con el LLM (DeepSeek vía
    OpenRouter, en JSON mode).
 3. Si falta algún dato obligatorio, genera una pregunta dinámica y el
    router de webhook la reenvía al productor por Telegram; el estado
    parcial se guarda en memoria (CONVERSACIONES) hasta completar los 4
    campos.

Nota de producción: el diccionario en memoria se pierde si el proceso se
reinicia. Para el MVP de hackathon es suficiente; si sobra tiempo, se puede
mover a una tabla `conversaciones` en Supabase con el mismo esquema.
"""
import json
import logging
from typing import Any

from agroia.integrations.llm_client import LLMError, pedir_json
from agroia.schemas import OfertaExtraida

logger = logging.getLogger(__name__)

# Estado conversacional simple: chat_id -> datos parciales acumulados
CONVERSACIONES: dict[str, dict[str, Any]] = {}

CAMPOS_OBLIGATORIOS = ["producto", "cantidad", "precio", "ubicacion"]
CAMPOS_EXTRAIBLES = ("producto", "cantidad", "unidad", "precio", "ubicacion")

SYSTEM_PROMPT = """Eres el Agente 1 de AgroIA Casanare: extraes datos estructurados
de ofertas de productos agropecuarios que campesinos escriben en lenguaje natural
(texto libre, a veces ya transcrito de una nota de voz).

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con esta forma:
{
  "producto": string o null,
  "cantidad": number o null,
  "unidad": string o null,
  "precio": number o null,
  "ubicacion": string o null
}

Reglas:
- "unidad": ej. "kg", "litros", "arrobas", "unidades".
- "precio": precio unitario en pesos colombianos, solo el número.
- "ubicacion": vereda o municipio, ej. "Yopal", "Aguazul".
- Si el mensaje no menciona un dato, dejá ese campo en null. No inventes valores.
- "cantidad" y "precio" deben ser números (sin símbolos de moneda ni texto).
- Combiná la información nueva del mensaje con los datos que ya se tenían
  (te los paso como contexto) para ir completando la oferta.
"""


def _extraer_con_llm(mensaje: str, datos_previos: dict[str, Any]) -> dict[str, Any]:
    """Devuelve los campos que el modelo logró extraer. `{}` si el modelo
    falló o no devolvió nada aprovechable (el flujo simplemente vuelve a
    preguntar por lo que falte)."""
    contexto = (
        f"Datos ya conocidos de esta oferta: {json.dumps(datos_previos, ensure_ascii=False)}\n"
        f'Nuevo mensaje del productor: "{mensaje}"'
    )
    try:
        datos = pedir_json(SYSTEM_PROMPT, contexto)
    except LLMError:
        logger.warning("Agente 1: el modelo no devolvió datos para %r", mensaje, exc_info=True)
        return {}
    return {k: datos.get(k) for k in CAMPOS_EXTRAIBLES if datos.get(k) is not None}


def _pregunta_por_campo_faltante(campo: str) -> str:
    preguntas = {
        "producto": "¿Qué producto quieres ofrecer?",
        "cantidad": "¿Qué cantidad tienes disponible? (ej. 20 kg, 5 arrobas)",
        "precio": "¿A qué precio lo vas a ofrecer?",
        "ubicacion": "¿Desde qué vereda o municipio lo ofreces?",
    }
    return preguntas.get(campo, f"Falta el dato: {campo}")


def procesar_mensaje_productor(chat_id: str, mensaje: str) -> OfertaExtraida:
    """Punto de entrada del Agente 1. Acumula estado por chat_id hasta que
    la oferta tiene los 4 campos obligatorios."""
    datos_previos = CONVERSACIONES.get(chat_id, {})
    datos_nuevos = _extraer_con_llm(mensaje, datos_previos)

    # Merge: un dato nuevo no-nulo sobreescribe al previo
    datos_combinados = {**datos_previos, **datos_nuevos}
    CONVERSACIONES[chat_id] = datos_combinados

    faltante = next((c for c in CAMPOS_OBLIGATORIOS if not datos_combinados.get(c)), None)

    if faltante:
        return OfertaExtraida(
            **datos_combinados,
            completo=False,
            pregunta_faltante=_pregunta_por_campo_faltante(faltante),
        )

    # Oferta completa: limpiar el estado conversacional
    CONVERSACIONES.pop(chat_id, None)
    return OfertaExtraida(**datos_combinados, completo=True)
