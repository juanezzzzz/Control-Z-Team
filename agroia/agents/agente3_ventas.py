"""Agente 3: Atención y Ventas (Comprador).

Interpreta un mensaje libre de un comprador (ej. "Busco plátano por Yopal"),
lo traduce a una consulta contra Supabase y arma la respuesta con las
mejores opciones + contacto directo del productor.

Diseño defensivo: ninguna falla externa (Claude caído, JSON raro, Supabase
sin responder) debe producir un 500. Si algo falla, el Agente 3 degrada a
una búsqueda más simple y, en el peor caso, responde con un texto útil y
`resultados: []`.
"""
import logging

from anthropic import Anthropic

from agroia.core.config import settings
from agroia.core.text_utils import extraer_json, normalizar
from agroia.repositories.productos_repository import buscar_productos
from agroia.schemas import ConsultaAgente3Out, ProductoOut

logger = logging.getLogger(__name__)

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Eres el Agente 3 de AgroIA Casanare: interpretas mensajes de
compradores que buscan productos agropecuarios y devuelves SOLO un JSON con
esta forma exacta, sin texto adicional:
{ "producto": string o null, "ubicacion": string o null }

Reglas:
- "producto": el bien buscado, en singular y sin adjetivos de más (ej. "plátano",
  "leche", "queso"). Si no se menciona, null.
- "ubicacion": vereda o municipio de Casanare (ej. "Yopal", "Aguazul",
  "Tauramena"). Si no se menciona, null.

Ejemplos:
"Busco plátano por Yopal" -> {"producto": "plátano", "ubicacion": "Yopal"}
"Necesito leche" -> {"producto": "leche", "ubicacion": null}
"¿Hay algo cerca de Aguazul?" -> {"producto": null, "ubicacion": "Aguazul"}
"""

_SIN_RESULTADOS = (
    "No encontré ofertas activas que coincidan con tu búsqueda por ahora. "
    "Intenta con otro producto o ubicación, o vuelve a consultar más tarde."
)


def _interpretar_intencion(mensaje: str) -> dict:
    """Extrae {producto, ubicacion} del mensaje usando Claude.

    Si Claude falla o devuelve algo no parseable, cae a una heurística:
    usar el mensaje completo (limpio) como término de producto.
    """
    try:
        resp = _client.messages.create(
            model=settings.CLAUDE_MODEL_VENTAS,
            max_tokens=150,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": mensaje}],
        )
        texto = resp.content[0].text.strip()
        datos = extraer_json(texto)
        return {
            "producto": _limpiar(datos.get("producto")),
            "ubicacion": _limpiar(datos.get("ubicacion")),
        }
    except Exception:  # noqa: BLE001
        logger.warning("Agente 3: fallback de intención para mensaje=%r", mensaje, exc_info=True)
        return {"producto": _heuristica_producto(mensaje), "ubicacion": None}


def _limpiar(valor) -> str | None:
    if not isinstance(valor, str):
        return None
    valor = valor.strip()
    return valor or None


# Palabras de relleno típicas de una consulta de compra: se quitan para que
# el término que va a la búsqueda sea lo más limpio posible en el fallback.
_RELLENO = {
    "busco", "buscar", "necesito", "necesitar", "quiero", "comprar", "consigo",
    "conseguir", "hay", "algo", "de", "del", "la", "el", "los", "las", "un",
    "una", "por", "en", "cerca", "para", "me", "interesa", "alguien", "vende",
    "tiene", "tienen", "kilos", "kg", "favor",
}


def _heuristica_producto(mensaje: str) -> str | None:
    palabras = [p for p in normalizar(mensaje).split() if p not in _RELLENO and not p.isdigit()]
    return " ".join(palabras) or None


def atender_consulta_comprador(mensaje: str) -> ConsultaAgente3Out:
    intencion = _interpretar_intencion(mensaje)

    try:
        resultados_db = buscar_productos(
            producto=intencion.get("producto"),
            ubicacion=intencion.get("ubicacion"),
        )
    except Exception:  # noqa: BLE001
        logger.error("Agente 3: la búsqueda en Supabase falló", exc_info=True)
        return ConsultaAgente3Out(
            respuesta_texto=(
                "Tuve un problema consultando el catálogo en este momento. "
                "Por favor intenta de nuevo en unos segundos."
            ),
            resultados=[],
        )

    resultados = [_a_producto_out(r) for r in resultados_db]
    resultados = _ordenar_por_relevancia(resultados, intencion)

    return ConsultaAgente3Out(
        respuesta_texto=_redactar_respuesta(resultados, intencion),
        resultados=resultados,
    )


def _a_producto_out(r: dict) -> ProductoOut:
    return ProductoOut(
        id=str(r["id"]),
        producto=r["producto"],
        cantidad=r.get("cantidad"),
        unidad=r.get("unidad"),
        precio=r.get("precio"),
        ubicacion=r.get("ubicacion"),
        telefono_contacto=r.get("telefono_contacto"),
        estado=r.get("estado", "activo"),
    )


def _ordenar_por_relevancia(resultados: list[ProductoOut], intencion: dict) -> list[ProductoOut]:
    """Refuerzo del orden que ya trae la RPC (y única fuente de orden en el
    fallback): primero coincidencia de ubicación, luego de producto."""
    prod = normalizar(intencion.get("producto"))
    ubic = normalizar(intencion.get("ubicacion"))

    def puntaje(p: ProductoOut) -> tuple:
        coincide_ubic = bool(ubic) and ubic in normalizar(p.ubicacion)
        coincide_prod = bool(prod) and (prod in normalizar(p.producto) or normalizar(p.producto) in prod)
        return (coincide_ubic, coincide_prod)

    return sorted(resultados, key=puntaje, reverse=True)


def _redactar_respuesta(resultados: list[ProductoOut], intencion: dict) -> str:
    if not resultados:
        return _SIN_RESULTADOS

    lineas = [f"Encontré {len(resultados)} oferta(s):", ""]
    for r in resultados:
        precio = f"${r.precio:,.0f}" if r.precio else "precio a consultar"
        cantidad = f"{_num(r.cantidad)} {r.unidad or ''}".strip() if r.cantidad else "cantidad a consultar"
        ubicacion = r.ubicacion or "ubicación no especificada"
        contacto = f"https://wa.me/{r.telefono_contacto}" if r.telefono_contacto else "contacto no disponible"
        lineas.append(f"• {r.producto.title()} — {cantidad} — {precio} — {ubicacion}")
        lineas.append(f"  Contacto: {contacto}")
    return "\n".join(lineas)


def _num(valor: float | None) -> str:
    """Muestra 20 en vez de 20.0 cuando la cantidad es entera."""
    if valor is None:
        return ""
    return str(int(valor)) if float(valor).is_integer() else str(valor)
