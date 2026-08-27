"""Agente 1: Recepción y Extracción de Datos (Productor).

Flujo (según el documento de arquitectura, sección 3):
 1. Si el mensaje es audio, ya llega transcrito a texto (ver
    agroia/integrations/speech_to_text.py).
 2. Extrae producto, cantidad, precio, ubicación con Gemini (function calling).
 3. Si falta algún dato obligatorio, genera una pregunta dinámica y el
    router de webhook la reenvía al productor por Telegram; el estado
    parcial se guarda en memoria (CONVERSACIONES) hasta completar los 4
    campos.

Nota de producción: el diccionario en memoria se pierde si el proceso se
reinicia. Para el MVP de hackathon es suficiente; si sobra tiempo, se puede
mover a una tabla `conversaciones` en Supabase con el mismo esquema.
"""
from typing import Any

from google import genai
from google.genai import types

from agroia.core.config import settings
from agroia.schemas import OfertaExtraida

# Estado conversacional simple: chat_id -> datos parciales acumulados
CONVERSACIONES: dict[str, dict[str, Any]] = {}

CAMPOS_OBLIGATORIOS = ["producto", "cantidad", "precio", "ubicacion"]

SYSTEM_PROMPT = """Eres el Agente 1 de AgroIA Casanare: extraes datos estructurados
de ofertas de productos agropecuarios que campesinos escriben en lenguaje natural
(texto libre, a veces ya transcrito de una nota de voz).

Llamá SIEMPRE a la herramienta extraer_oferta con los datos encontrados.

Reglas:
- Si el mensaje no menciona un dato, dejá ese campo en null. No inventes valores.
- "cantidad" y "precio" deben ser números (sin símbolos de moneda ni texto).
- Combiná la información nueva del mensaje con los datos que ya se tenían
  (te los paso como contexto) para ir completando la oferta.
"""

EXTRAER_OFERTA = types.FunctionDeclaration(
    name="extraer_oferta",
    description="Extrae los datos de una oferta de producto agropecuario a partir del mensaje de un productor.",
    parameters={
        "type": "OBJECT",
        "properties": {
            "producto": {
                "type": "STRING",
                "nullable": True,
                "description": "Nombre del producto ofrecido.",
            },
            "cantidad": {
                "type": "NUMBER",
                "nullable": True,
                "description": "Cantidad disponible, como número puro.",
            },
            "unidad": {
                "type": "STRING",
                "nullable": True,
                "description": "Unidad de la cantidad (ej. 'kg', 'litros', 'arrobas', 'unidades').",
            },
            "precio": {
                "type": "NUMBER",
                "nullable": True,
                "description": "Precio unitario en pesos colombianos, solo el número.",
            },
            "ubicacion": {
                "type": "STRING",
                "nullable": True,
                "description": "Vereda o municipio desde donde se ofrece (ej. 'Yopal', 'Aguazul').",
            },
        },
        "required": ["producto", "cantidad", "unidad", "precio", "ubicacion"],
    },
)


def _extraer_con_gemini(mensaje: str, datos_previos: dict[str, Any]) -> dict[str, Any]:
    contexto = (
        f"Datos ya conocidos de esta oferta: {datos_previos}\n"
        f"Nuevo mensaje del productor: \"{mensaje}\""
    )
    # Nota: se crea un cliente nuevo por llamada a propósito. Reusar una
    # instancia de genai.Client entre requests dispara un 503 espurio en la
    # segunda llamada (bug de reuso de conexión HTTP/2 de google-genai +
    # httpx en Windows/Python 3.14, verificado en este entorno).
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL_EXTRACCION,
        contents=contexto,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=[EXTRAER_OFERTA])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode="ANY",
                    allowed_function_names=["extraer_oferta"],
                )
            ),
        ),
    )

    candidate = response.candidates[0] if response.candidates else None
    parts = candidate.content.parts if candidate and candidate.content else []
    for part in parts:
        if part.function_call and part.function_call.name == "extraer_oferta":
            return dict(part.function_call.args)

    return {}


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
    datos_nuevos = _extraer_con_gemini(mensaje, datos_previos)

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
