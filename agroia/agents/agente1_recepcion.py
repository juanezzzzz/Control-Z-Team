"""Agente 1: Recepción y Extracción de Datos (Productor).

Flujo (según el documento de arquitectura, sección 3):
 1. Si el mensaje es audio, ya llega transcrito a texto (ver
    agroia/integrations/speech_to_text.py).
 2. Extrae producto, cantidad, precio, ubicación con Claude.
 3. Si falta algún dato obligatorio, genera una pregunta dinámica y el
    router de webhook la reenvía al productor por Telegram; el estado
    parcial se guarda en memoria (CONVERSACIONES) hasta completar los 4
    campos.

Nota de producción: el diccionario en memoria se pierde si el proceso se
reinicia. Para el MVP de hackathon es suficiente; si sobra tiempo, se puede
mover a una tabla `conversaciones` en Supabase con el mismo esquema.
"""
import json
from typing import Any

from anthropic import Anthropic

from agroia.core.config import settings
from agroia.schemas import OfertaExtraida

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Estado conversacional simple: chat_id -> datos parciales acumulados
CONVERSACIONES: dict[str, dict[str, Any]] = {}

CAMPOS_OBLIGATORIOS = ["producto", "cantidad", "precio", "ubicacion"]

SYSTEM_PROMPT = """Eres el Agente 1 de AgroIA Casanare: extraes datos estructurados
de ofertas de productos agropecuarios que campesinos escriben en lenguaje natural
(texto libre, a veces ya transcrito de una nota de voz).

Debes responder ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con
esta forma exacta:
{
  "producto": string o null,
  "cantidad": number o null,
  "unidad": string o null (ej. "kg", "litros", "arrobas", "unidades"),
  "precio": number o null (precio unitario en pesos colombianos, solo el número),
  "ubicacion": string o null (vereda/municipio, ej. "Yopal", "Aguazul")
}

Reglas:
- Si el mensaje no menciona un dato, deja ese campo en null. No inventes valores.
- "cantidad" y "precio" deben ser números (sin símbolos de moneda ni texto).
- Combina la información nueva del mensaje con los datos que ya se tenían
  (te los paso como contexto) para ir completando la oferta.
"""


def _extraer_con_claude(mensaje: str, datos_previos: dict[str, Any]) -> dict[str, Any]:
    contexto = (
        f"Datos ya conocidos de esta oferta: {json.dumps(datos_previos, ensure_ascii=False)}\n"
        f"Nuevo mensaje del productor: \"{mensaje}\""
    )
    resp = _client.messages.create(
        model=settings.CLAUDE_MODEL_EXTRACCION,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": contexto}],
    )
    texto = resp.content[0].text.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        # Fallback defensivo si el modelo agrega texto extra pese al system prompt
        inicio, fin = texto.find("{"), texto.rfind("}")
        return json.loads(texto[inicio : fin + 1])


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
    datos_nuevos = _extraer_con_claude(mensaje, datos_previos)

    # Merge: un dato nuevo no-nulo sobreescribe al previo
    datos_combinados = {**datos_previos, **{k: v for k, v in datos_nuevos.items() if v is not None}}
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
