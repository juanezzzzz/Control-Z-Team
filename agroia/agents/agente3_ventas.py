"""Agente 3: Atención y Ventas (Comprador).

Interpreta un mensaje libre de un comprador (ej. "Busco plátano por Yopal"),
lo traduce a una consulta contra Supabase y arma la respuesta con las
mejores opciones + contacto directo del productor.
"""
import json

from anthropic import Anthropic

from agroia.core.config import settings
from agroia.repositories.productos_repository import buscar_productos
from agroia.schemas import ConsultaAgente3Out, ProductoOut

_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """Eres el Agente 3 de AgroIA Casanare: interpretas mensajes de
compradores que buscan productos agropecuarios y devuelves SOLO un JSON con
esta forma exacta:
{ "producto": string o null, "ubicacion": string o null }

Ejemplos:
"Busco plátano por Yopal" -> {"producto": "plátano", "ubicacion": "Yopal"}
"Necesito leche" -> {"producto": "leche", "ubicacion": null}
"""


def _interpretar_intencion(mensaje: str) -> dict:
    resp = _client.messages.create(
        model=settings.CLAUDE_MODEL_VENTAS,
        max_tokens=150,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": mensaje}],
    )
    texto = resp.content[0].text.strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        inicio, fin = texto.find("{"), texto.rfind("}")
        return json.loads(texto[inicio : fin + 1])


def atender_consulta_comprador(mensaje: str) -> ConsultaAgente3Out:
    intencion = _interpretar_intencion(mensaje)
    resultados_db = buscar_productos(
        producto=intencion.get("producto"),
        ubicacion=intencion.get("ubicacion"),
    )
    resultados = [
        ProductoOut(
            id=str(r["id"]),
            producto=r["producto"],
            cantidad=r.get("cantidad"),
            unidad=r.get("unidad"),
            precio=r.get("precio"),
            ubicacion=r.get("ubicacion"),
            telefono_contacto=r.get("telefono_contacto"),
            estado=r.get("estado", "activo"),
        )
        for r in resultados_db
    ]

    if not resultados:
        texto = "No encontré ofertas activas que coincidan con tu búsqueda por ahora. ¡Vuelve a intentar más tarde!"
    else:
        lineas = [f"Encontré {len(resultados)} oferta(s):\n"]
        for r in resultados:
            precio = f"${r.precio:,.0f}" if r.precio else "precio a consultar"
            cantidad = f"{r.cantidad} {r.unidad or ''}".strip() if r.cantidad else ""
            contacto = f"wa.me/{r.telefono_contacto}" if r.telefono_contacto else "contacto no disponible"
            lineas.append(f"• {r.producto.title()} - {cantidad} - {precio} - {r.ubicacion}\n  Contacto: {contacto}")
        texto = "\n".join(lineas)

    return ConsultaAgente3Out(respuesta_texto=texto, resultados=resultados)
