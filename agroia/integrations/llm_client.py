"""Cliente LLM compartido — OpenRouter (API compatible con OpenAI).

Todos los agentes que necesitan un modelo de lenguaje pasan por acá. Hoy
apunta a DeepSeek V3.1 en el tier gratuito de OpenRouter
(`deepseek/deepseek-chat-v3.1:free`).

Se usa "JSON mode" (`response_format={"type": "json_object"}`) en lugar de
function calling porque es lo que soportan de forma consistente los modelos
`:free` de OpenRouter. Cada agente describe en su system prompt la forma
exacta del JSON que espera.
"""
import logging

from openai import OpenAI

from agroia.core.config import settings
from agroia.core.text_utils import extraer_json

logger = logging.getLogger(__name__)

# OpenRouter recomienda (no obliga) identificar la app que hace la llamada.
_HEADERS = {
    "HTTP-Referer": "https://github.com/juanezzzzz/Control-Z-Team",
    "X-Title": "AgroIA Casanare",
}


class LLMError(RuntimeError):
    """El modelo no respondió, o no devolvió un objeto JSON aprovechable."""


def _client() -> OpenAI:
    if not settings.OPENROUTER_API_KEY:
        raise LLMError("Falta OPENROUTER_API_KEY: consíguela en https://openrouter.ai/keys")
    return OpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        default_headers=_HEADERS,
        timeout=settings.LLM_TIMEOUT,
    )


def pedir_json(system_prompt: str, user_content: str) -> dict:
    """Le pide al modelo una respuesta en JSON y devuelve el objeto parseado.

    Lanza `LLMError` si la llamada falla (red, 429, auth) o si la respuesta
    no trae un objeto JSON. Los agentes atrapan `LLMError` y degradan.
    """
    try:
        resp = _client().chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
    except LLMError:
        raise
    except Exception as exc:  # noqa: BLE001 — red, rate limit, auth, etc.
        raise LLMError(f"Fallo llamando al modelo: {exc}") from exc

    contenido = (resp.choices[0].message.content or "") if resp.choices else ""
    try:
        return extraer_json(contenido)
    except ValueError as exc:
        raise LLMError(f"El modelo no devolvió JSON: {exc}") from exc
