"""Clasificador de intención: decide a qué agente enrutar un mensaje.

Reemplaza la heurística de palabras clave que traía el MVP. Esa heurística
tenía un problema de fondo: era binaria (compra / no-compra), así que
CUALQUIER mensaje no reconocido —incluido un simple "hola"— caía al flujo de
productor y el bot respondía preguntando qué querían vender.

Acá la clasificación tiene tres salidas y una de ellas es "no sé": ante la
duda se le pregunta al usuario en vez de adivinar.

Se usa el LLM porque las formas de pedir algo son demasiadas para una lista
("¿cuánto vale la papa?", "¿me vendes plátano?", "quién tiene yuca"). Si el
LLM falla se cae a las palabras clave, que siguen sirviendo para los casos
más comunes.
"""
import logging

from agroia.core.text_utils import normalizar
from agroia.integrations.llm_client import LLMError, pedir_json

logger = logging.getLogger(__name__)

COMPRA = "compra"
VENTA = "venta"
DESCONOCIDA = "desconocida"

_VALIDAS = {COMPRA, VENTA, DESCONOCIDA}

SYSTEM_PROMPT = """Eres el enrutador de AgroIA Casanare, un mercado agrícola por
Telegram. Clasificás la intención del mensaje de un usuario.

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional:
{ "intencion": "compra" | "venta" | "desconocida" }

Criterios:
- "venta": el usuario OFRECE un producto suyo. Ej: "tengo 20 kg de papa",
  "vendo plátano a 2000", "quiero publicar mi cosecha de yuca".
- "compra": el usuario BUSCA comprar algo. Ej: "busco plátano por Yopal",
  "¿cuánto vale la papa?", "¿quién tiene yuca?", "necesito leche",
  "¿me vendes queso?", "estoy interesado en arroz".
- "desconocida": saludos ("hola", "buenas"), preguntas sobre el bot ("¿qué
  haces?", "ayuda"), agradecimientos, o cualquier mensaje del que NO se pueda
  deducir con confianza si quiere comprar o vender.

Ante la duda respondé "desconocida". Es mejor preguntarle al usuario que
mandarlo al flujo equivocado.
"""

# Respaldo por palabras clave para cuando el LLM no responde. Deliberadamente
# conservador: si no hay coincidencia clara devuelve DESCONOCIDA.
_PALABRAS_COMPRA = (
    "busco", "buscando", "necesito", "necesitando", "quiero comprar",
    "estoy buscando", "alguien vende", "alguien tiene", "donde consigo",
    "donde puedo conseguir", "quien vende", "quien tiene", "me interesa comprar",
    "cuanto vale", "cuanto cuesta", "me vendes", "hay ",
)
_PALABRAS_VENTA = (
    "vendo", "tengo", "ofrezco", "quiero vender", "estoy vendiendo",
    "dispongo de", "quiero publicar",
)


def _coincide(texto_normalizado: str, palabras: tuple[str, ...]) -> bool:
    return any(
        texto_normalizado.startswith(p) or f" {p}" in f" {texto_normalizado} "
        for p in palabras
    )


def _clasificar_por_palabras(texto: str) -> str:
    """Respaldo sin LLM. La venta gana sobre la compra porque 'tengo' aparece
    en ambas familias ('tengo papa' vs '¿quién tiene papa?')."""
    t = normalizar(texto)
    if _coincide(t, _PALABRAS_VENTA):
        return VENTA
    if _coincide(t, _PALABRAS_COMPRA):
        return COMPRA
    return DESCONOCIDA


# Verbos que abren un mensaje sin ninguna ambigüedad sobre qué quiere hacer
# la persona. Solo se usan cuando ARRANCAN el mensaje: "vendo papa" es
# inequívoco, pero "tengo" no entra acá porque "tengo una pregunta" no es una
# oferta.
_APERTURAS_INEQUIVOCAS = (
    ("vendo", VENTA),
    ("ofrezco", VENTA),
    ("quiero vender", VENTA),
    ("busco", COMPRA),
    ("necesito", COMPRA),
    ("quiero comprar", COMPRA),
)


def _apertura_inequivoca(texto: str) -> str | None:
    t = normalizar(texto)
    for prefijo, intencion in _APERTURAS_INEQUIVOCAS:
        if t.startswith(prefijo):
            return intencion
    return None


def clasificar_intencion(texto: str) -> str:
    """Devuelve COMPRA, VENTA o DESCONOCIDA. Nunca lanza excepción."""
    try:
        datos = pedir_json(SYSTEM_PROMPT, texto)
        intencion = str(datos.get("intencion", "")).strip().lower()
        if intencion in _VALIDAS:
            # El modelo a veces contesta "desconocida" ante un mensaje que
            # menciona algo fuera de dominio (un computador, un artículo para
            # adultos), aunque la intención sea evidente. Devolver el menú ahí
            # confunde: la persona dijo claramente que quería vender. Si el
            # mensaje ABRE con un verbo inequívoco, se confía en eso y el
            # filtro de productos se encarga de explicarle que no se publica.
            if intencion == DESCONOCIDA:
                return _apertura_inequivoca(texto) or DESCONOCIDA
            return intencion
        logger.warning("Clasificador: intención no reconocida %r", intencion)
    except LLMError:
        logger.warning("Clasificador: el LLM falló, uso palabras clave", exc_info=True)
    return _clasificar_por_palabras(texto)
