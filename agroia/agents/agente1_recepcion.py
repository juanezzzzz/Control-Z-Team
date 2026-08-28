"""Agente 1: Recepción y Extracción de Datos (Productor).

Flujo (según el documento de arquitectura, sección 3):
 1. Si el mensaje es audio, ya llega transcrito a texto (ver
    agroia/integrations/speech_to_text.py).
 2. Extrae producto, cantidad, precio, ubicación, nombre y teléfono de
    contacto con el LLM (vía OpenRouter, en JSON mode).
 3. Valida lo extraído (ver `_VALIDADORES`). Un dato que no pasa NO se
    guarda: se le pide amablemente al productor que lo repita, explicándole
    qué fue lo que no cuadró.
 4. Si falta algún dato obligatorio, arma una respuesta humanizada (saluda
    según la hora en el primer mensaje, reconoce lo que ya contó el
    productor y pregunta TODO lo que falta en una sola frase, no campo por
    campo) y el router de webhook la reenvía por Telegram; el estado
    parcial se guarda en memoria (CONVERSACIONES) hasta completar los 6
    campos.

`direccion_local` es opcional: se ofrece al final de la pregunta pero nunca
bloquea la publicación — muchos campesinos venden desde la finca y no tienen
un local con dirección.

Nota de producción: el diccionario en memoria se pierde si el proceso se
reinicia. Para el MVP de hackathon es suficiente; si sobra tiempo, se puede
mover a una tabla `conversaciones` en Supabase con el mismo esquema.
"""
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from agroia.agents.normalizacion import MUNICIPIOS_CASANARE, normalizar_ubicacion
from agroia.integrations.llm_client import LLMError, pedir_json
from agroia.schemas import OfertaExtraida

logger = logging.getLogger(__name__)

# Colombia es UTC-5 todo el año (no tiene horario de verano), así que un
# offset fijo alcanza y evita depender del paquete `tzdata` en Windows.
_HORA_COLOMBIA = timezone(timedelta(hours=-5))

# Estado conversacional simple: chat_id -> datos parciales acumulados
CONVERSACIONES: dict[str, dict[str, Any]] = {}

CAMPOS_OBLIGATORIOS = [
    "producto", "cantidad", "precio", "ubicacion", "nombre_productor", "telefono_contacto",
]
CAMPOS_EXTRAIBLES = (
    "producto", "cantidad", "unidad", "precio", "ubicacion",
    "nombre_productor", "telefono_contacto", "direccion_local",
)

SYSTEM_PROMPT = """Eres el Agente 1 de AgroIA Casanare: extraes datos estructurados
de ofertas de productos agropecuarios que campesinos escriben en lenguaje natural
(texto libre, a veces ya transcrito de una nota de voz).

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional, con esta forma:
{
  "producto": string o null,
  "cantidad": number o null,
  "unidad": string o null,
  "precio": number o null,
  "ubicacion": string o null,
  "nombre_productor": string o null,
  "telefono_contacto": string o null,
  "direccion_local": string o null
}

Reglas:
- "unidad": ej. "kg", "litros", "arrobas", "unidades".
- "precio": precio unitario en pesos colombianos, solo el número.
- "ubicacion": municipio de Casanare, o vereda + municipio (ej. "Yopal",
  "Vereda El Charte, Yopal"). AgroIA solo publica ofertas de Casanare: si el
  productor menciona un lugar de otro departamento, ponelo igual y el sistema
  se encarga de avisarle. No inventes el municipio si solo dio la vereda.
- "nombre_productor": el nombre de la persona que ofrece el producto (quien
  escribe), ej. "Juan Pérez". No es el nombre del producto ni del comprador.
- "telefono_contacto": el número de teléfono o WhatsApp donde los compradores
  pueden contactar al productor. Solo dígitos (con indicativo si lo da, ej.
  "573001234567"); quita espacios, guiones y símbolos.
- "direccion_local": dirección del local, puesto o finca donde el comprador
  puede ir a comprar en persona (ej. "Calle 20 #5-30, plaza de mercado" o
  "Finca La Esperanza, km 3 vía Nunchía"). Es OPCIONAL: si el productor dice
  que no tiene local o que no aplica, dejalo en null.
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


_FRASES_CAMPO_FALTANTE = {
    "producto": "qué producto ofreces",
    "cantidad": "qué cantidad tienes disponible (por ejemplo, 20 kg o 5 arrobas)",
    "precio": "a qué precio lo vendes",
    "ubicacion": "desde qué municipio de Casanare lo ofreces (y la vereda, si aplica)",
    "nombre_productor": "cuál es tu nombre",
    "telefono_contacto": "a qué número de teléfono o WhatsApp te pueden contactar los compradores",
}

# Invitación al dato opcional. Se agrega al final de la pregunta, redactada
# para que quede claro que se puede omitir sin problema.
_INVITACION_DIRECCION = (
    "Y si tienes un local o finca donde te puedan visitar, cuéntame la "
    "dirección para agregarla; si no, no hay problema."
)

# Rangos de sensatez, no de negocio: atrapan un dedo pegado en el teclado o
# una transcripción de voz que salió mal, no limitan a un productor grande.
# Los topes duros de publicación viven en el Agente 2 (validar_oferta).
_CANTIDAD_MAXIMA = 1_000_000
_PRECIO_MAXIMO = 100_000_000


def _validar_telefono(valor: Any) -> str | None:
    """Un celular colombiano tiene 10 dígitos (3XX XXX XXXX); con indicativo
    de país son 12 (57...). Un fijo puede tener 7 u 8. Se acepta ese rango
    amplio a propósito: el objetivo es atrapar un número imposible, no
    rechazar a alguien por un formato raro pero válido."""
    digitos = re.sub(r"\D", "", str(valor))
    if not digitos:
        return "el número de contacto que me diste no tiene ningún dígito"
    if len(digitos) < 7:
        return f"el número de contacto que me diste ({valor}) parece muy corto"
    if len(digitos) > 13:
        return f"el número de contacto que me diste ({valor}) parece muy largo"
    if len(set(digitos)) == 1:
        return f"el número de contacto que me diste ({valor}) parece incompleto"
    return None


def _validar_nombre(valor: Any) -> str | None:
    texto = str(valor).strip()
    if len(texto) < 2:
        return "el nombre que me diste parece muy corto"
    if not any(c.isalpha() for c in texto):
        return f"el nombre que me diste ({texto}) no parece un nombre"
    return None


def _validar_ubicacion(valor: Any) -> str | None:
    """AgroIA es un mercado de Casanare: solo se publican ofertas del
    departamento. Se acepta el municipio solo ("Yopal") o una vereda que lo
    mencione ("Vereda El Charte, Yopal").

    Una vereda suelta ("Vereda La Niata") se rechaza a propósito: no hay forma
    de saber si queda en Casanare, y sin municipio la oferta no aparecería en
    el filtro por zona del catálogo.
    """
    texto = str(valor).strip()
    if not texto:
        return "no entendí la ubicación"
    _, municipio = normalizar_ubicacion(texto)
    if municipio is None:
        return (
            f"no reconocí un municipio de Casanare en «{texto}» "
            f"(por ejemplo: {', '.join(MUNICIPIOS_CASANARE[:3])}…)"
        )
    return None


def _validar_cantidad(valor: Any) -> str | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return f"no entendí la cantidad ({valor})"
    if numero <= 0:
        return "la cantidad debe ser mayor que cero"
    if numero > _CANTIDAD_MAXIMA:
        return f"la cantidad que me diste ({numero:g}) parece demasiado grande"
    return None


def _validar_precio(valor: Any) -> str | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return f"no entendí el precio ({valor})"
    if numero <= 0:
        return "el precio debe ser mayor que cero"
    if numero > _PRECIO_MAXIMO:
        return f"el precio que me diste ({numero:g}) parece demasiado alto"
    return None


# Campo -> validador. Un campo sin validador se acepta tal cual.
_VALIDADORES = {
    "telefono_contacto": _validar_telefono,
    "nombre_productor": _validar_nombre,
    "ubicacion": _validar_ubicacion,
    "cantidad": _validar_cantidad,
    "precio": _validar_precio,
}


def _separar_validos(datos: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Parte lo extraído en (lo que se puede guardar, {campo: motivo} rechazado).

    Un dato que no pasa la validación NO se guarda: así el productor vuelve a
    ver la pregunta por ese campo en vez de quedar con un teléfono imposible
    publicado en el catálogo.
    """
    validos: dict[str, Any] = {}
    rechazos: dict[str, str] = {}
    for campo, valor in datos.items():
        problema = _VALIDADORES.get(campo, lambda _: None)(valor)
        if problema:
            rechazos[campo] = problema
        else:
            validos[campo] = valor
    return validos, rechazos


def _saludo_segun_hora() -> str:
    """Saludo natural según la hora local en Colombia."""
    hora = datetime.now(_HORA_COLOMBIA).hour
    if 5 <= hora < 12:
        return "¡Buenos días!"
    if 12 <= hora < 19:
        return "¡Buenas tardes!"
    return "¡Buenas noches!"


def _unir_en_espanol(frases: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b y c' (y ['a'] -> 'a')."""
    if len(frases) == 1:
        return frases[0]
    return ", ".join(frases[:-1]) + " y " + frases[-1]


def _resumen_lo_ya_dicho(datos: dict[str, Any]) -> str | None:
    """Frase corta reconociendo lo que el productor ya contó (ej. "4 kg de
    papa"), para que la respuesta no ignore lo que acaba de escribir."""
    if not datos.get("producto"):
        return None
    cantidad = datos.get("cantidad")
    if cantidad:
        unidad = datos.get("unidad") or "kg"
        return f"{cantidad:g} {unidad} de {datos['producto']}"
    return str(datos["producto"])


def _mensaje_pregunta_faltantes(
    datos: dict[str, Any],
    campos_faltantes: list[str],
    es_primer_mensaje: bool,
    motivos_rechazo: list[str] | None = None,
) -> str:
    """Arma una respuesta educada y natural pidiendo TODO lo que falta en una
    sola frase (en vez de un campo por mensaje), saludando según la hora si
    es el primer mensaje de la conversación y reconociendo lo que ya se sabe.

    Si algún dato llegó mal (`motivos_rechazo`), lo dice primero y con
    disculpa, para que el productor entienda por qué se le vuelve a preguntar
    en vez de sentir que el bot lo ignoró.
    """
    pregunta = f"¿Me podrías decir {_unir_en_espanol([_FRASES_CAMPO_FALTANTE[c] for c in campos_faltantes])}?"
    resumen = _resumen_lo_ya_dicho(datos)

    partes = []
    if motivos_rechazo:
        # Prevalece la disculpa sobre el saludo: si algo salió mal, lo primero
        # que debe leer el productor es qué fue y que no fue culpa suya.
        partes.append(f"Disculpa, {_unir_en_espanol(motivos_rechazo)}.")
    elif es_primer_mensaje:
        partes.append(_saludo_segun_hora())
        partes.append(
            f"Perfecto, ya tengo anotado que ofreces {resumen}."
            if resumen else "Con gusto te ayudo a publicar tu oferta."
        )
    elif resumen:
        partes.append(f"¡Gracias! Ya tengo anotado que ofreces {resumen}.")
    else:
        partes.append("¡Gracias!")
    partes.append(pregunta)

    # La dirección es opcional: se ofrece solo cuando ya no falta nada más
    # obligatorio aparte de ella, para no alargar una pregunta que ya es larga.
    if "direccion_local" not in datos and len(campos_faltantes) <= 2:
        partes.append(_INVITACION_DIRECCION)

    return " ".join(partes)


def procesar_mensaje_productor(chat_id: str, mensaje: str) -> OfertaExtraida:
    """Punto de entrada del Agente 1. Acumula estado por chat_id hasta que
    la oferta tiene los 6 campos obligatorios."""
    es_primer_mensaje = chat_id not in CONVERSACIONES
    datos_previos = CONVERSACIONES.get(chat_id, {})
    datos_nuevos = _extraer_con_llm(mensaje, datos_previos)

    # Lo que no pasa la validación no se guarda: se le vuelve a preguntar al
    # productor explicándole qué no cuadró.
    datos_validos, rechazos = _separar_validos(datos_nuevos)
    if rechazos:
        logger.info("Agente 1: datos rechazados de %s: %s", chat_id, rechazos)

    # Merge: un dato nuevo no-nulo sobreescribe al previo
    datos_combinados = {**datos_previos, **datos_validos}
    CONVERSACIONES[chat_id] = datos_combinados

    # Un campo rechazado se vuelve a preguntar aunque ya hubiera un valor
    # válido de un turno anterior: el productor estaba intentando corregirlo,
    # y publicar con el valor viejo sin avisarle sería ignorarlo en silencio.
    campos_faltantes = [
        c for c in CAMPOS_OBLIGATORIOS if not datos_combinados.get(c) or c in rechazos
    ]

    if campos_faltantes:
        return OfertaExtraida(
            **datos_combinados,
            completo=False,
            pregunta_faltante=_mensaje_pregunta_faltantes(
                datos_combinados, campos_faltantes, es_primer_mensaje, list(rechazos.values())
            ),
        )

    # Oferta completa: limpiar el estado conversacional
    CONVERSACIONES.pop(chat_id, None)
    return OfertaExtraida(**datos_combinados, completo=True)
