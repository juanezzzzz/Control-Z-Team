"""Adaptación de los mensajes del bot para que suenen bien dichos en voz alta.

Un texto escrito para leerse en pantalla suena mal leído por un sintetizador:
"$2.000" se pronuncia como un decimal o como dólares, "20 kg" como dos letras,
y un enlace `wa.me/57300...` es ruido puro. Este módulo traduce el mensaje
escrito a un mensaje *hablable*, y le da el tono llanero neutro que usa el bot.

Todo acá es texto puro, sin red ni I/O: se prueba sin llamar al sintetizador
(ver tests/test_voz.py).
"""
import re

# ---------------------------------------------------------------------------
# Tono llanero neutro
# ---------------------------------------------------------------------------

# Toques léxicos del habla llanera (Casanare/Arauca/Meta) escogidos con dos
# criterios: que suenen naturales y que NO caigan en caricatura. Se evitan a
# propósito los regionalismos muy marcados ("catire", "cachilapo", "guate") y
# el exceso de "pues": el objetivo es un llanero neutro, cercano pero sobrio.
#
# Se aplican solo a la versión hablada; el texto escrito queda igual, porque
# es el que la persona relee para copiar un teléfono o un precio.
_TONO_LLANERO: tuple[tuple[str, str], ...] = (
    # Saludo: "buenas" es el saludo llanero por excelencia, a toda hora.
    (r"\B¡Hola!", "¡Buenas!"),
    (r"\bHola\b", "Buenas"),
    # "hallar" se usa mucho más que "encontrar" en el Llano. El orden importa:
    # "No encontré" debe resolverse antes que el "Encontré" suelto.
    (r"\bNo encontré\b", "No le hallé"),
    (r"\bEncontré\b", "Le hallé"),
    (r"\bencontré\b", "le hallé"),
    # Confirmación cálida sin sobrecargar.
    (r"\B¡Listo!", "¡Listo pues!"),
    # Trato respetuoso habitual entre productores y compradores del Llano.
    (r"\bLos compradores\b", "Los compradores, vecino,"),
)


def dar_tono_llanero(texto: str) -> str:
    """Aplica los toques de habla llanera a un mensaje ya escrito.

    Son sustituciones léxicas, nunca cambios de conjugación: reescribir
    tú → usted automáticamente rompe los verbos, así que eso se decide al
    redactar cada mensaje, no acá.
    """
    for patron, reemplazo in _TONO_LLANERO:
        texto = re.sub(patron, reemplazo, texto)
    return texto


# ---------------------------------------------------------------------------
# De texto escrito a texto hablable
# ---------------------------------------------------------------------------

# Abreviaturas de unidad que el Agente 2 deja en su forma canónica. Las que ya
# son palabras completas (arroba, bulto, docena…) no necesitan traducción.
_UNIDADES_HABLADAS: tuple[tuple[str, str], ...] = (
    (r"\bkg\b", "kilos"),
    (r"\bgr?\b", "gramos"),
    (r"\blbs?\b", "libras"),
    (r"\bml\b", "mililitros"),
    (r"\bL\b", "litros"),
    (r"\bund?s?\b", "unidades"),
    (r"@", "arrobas"),
)

# Un enlace se borra JUNTO con la etiqueta que lo introduce ("Contacto: wa.me/…"),
# porque dejar el "Contacto:" suelto suena como una frase cortada a la mitad.
# La etiqueta es opcional y debe ir pegada al enlace: así se borra "Contacto:"
# pero nunca un "ofertas:" que sí tiene contenido detrás.
_URL = re.compile(
    r"(?:\b[^\W\d_]+\s*:)?\s*(?:https?://|www\.|wa\.me/)\S+",
    re.IGNORECASE,
)

# Emojis y símbolos decorativos: el sintetizador los lee como "signo de..." o
# los ignora de forma impredecible.
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF•→✓]+"
)

# "por kilos" no lo dice nadie: en español el precio va "a 2000 pesos EL KILO".
# La expansión de unidades pluraliza siempre (correcto en "20 kilos"), así que
# acá se corrige el caso del precio, que pide singular con artículo.
_UNIDAD_DE_PRECIO: tuple[tuple[str, str], ...] = (
    (r"\bpor kilos\b", "el kilo"),
    (r"\bpor gramos\b", "el gramo"),
    (r"\bpor libras\b", "la libra"),
    (r"\bpor litros\b", "el litro"),
    (r"\bpor mililitros\b", "el mililitro"),
    (r"\bpor unidades\b", "la unidad"),
    (r"\bpor arrobas\b", "la arroba"),
    (r"\bpor bultos\b", "el bulto"),
    (r"\bpor docenas\b", "la docena"),
    (r"\bpor toneladas\b", "la tonelada"),
)

# Los resultados del Agente 3 llegan como viñetas. Leídas de corrido suenan a
# volcado de base de datos; enumerarlas es lo que haría una persona al
# contarlas por teléfono. El Agente 3 devuelve máximo 5.
#
# Van con coma y no con dos puntos: los dos puntos abren una pausa larga y la
# lista sale a tirones. Con coma queda una sola pausa breve por oferta.
_ORDINALES = ("La primera,", "La segunda,", "La tercera,", "La cuarta,", "La quinta,")

# Miles con punto (formato colombiano): "2.000" -> "2000". El sintetizador lee
# bien un entero pelado; con el punto puede interpretarlo como decimal.
_MILES = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b")

# Celular colombiano de 10 dígitos: dicho como un número gigante es inservible.
# Separado en dígitos, el sintetizador lo dicta uno por uno y se puede anotar.
_CELULAR = re.compile(r"\b3\d{9}\b")


def _quitar_miles(match: re.Match) -> str:
    return match.group(0).replace(".", "")


def _dictar_digitos(match: re.Match) -> str:
    return " ".join(match.group(0))


def _enumerar_vinetas(texto: str) -> str:
    """Cambia las viñetas por ordinales hablados.

    "• Plátano… • Yuca…" -> "La primera: Plátano… La segunda: Yuca…"

    Sin esto la lista se lee de corrido y suena a volcado de base de datos.
    Enumerar es lo que haría una persona contando las ofertas por teléfono, y
    además le da al sintetizador un punto natural donde respirar.
    """
    if "•" not in texto:
        return texto

    partes = texto.split("•")
    resultado = [partes[0].rstrip()]

    for i, parte in enumerate(partes[1:]):
        etiqueta = _ORDINALES[i] if i < len(_ORDINALES) else "Y otra,"
        resultado.append(f" {etiqueta}{parte.rstrip()}")

    return "".join(resultado)


def unir_campos(texto: str) -> str:
    """Une los campos de una oferta con preposiciones, no con comas.

    El Agente 3 arma cada resultado como "Producto - cantidad - precio -
    ubicación". Separado por comas, el sintetizador hace una pausa en cada
    una y la frase sale entrecortada; con preposiciones sale de corrido,
    como la diría una persona:

        "Plátano - 20 kg - $2.000 - Yopal"
        -> "Plátano de 20 kilos a 2000 pesos en Yopal"

    El orden de los reemplazos es el que desambigua: el precio se reconoce
    por el "$", la cantidad por empezar en dígito, y lo que quede es la
    ubicación.
    """
    texto = re.sub(r"\s+-\s+(?=\$)", " a ", texto)      # precio
    texto = re.sub(r"\s+-\s+(?=\d)", " de ", texto)     # cantidad
    return re.sub(r"\s+-\s+", " en ", texto)            # ubicación


def dar_fluidez(texto: str) -> str:
    """Quita los tropiezos que hacen sonar el texto a máquina leyendo.

    Dos cosas delatan al sintetizador, y ninguna es la voz:

    1. La concordancia. "A 2000 pesos por kilos" no lo dice nadie; se dice
       "el kilo". La expansión de unidades pluraliza siempre, correcto en
       "20 kilos" pero no en el precio.
    2. El exceso de comas. Cada una es una pausa: una frase con cuatro comas
       sale a tirones. Por eso los campos se unen con preposiciones
       (`unir_campos`) y acá no se agrega ninguna pausa nueva.
    """
    for patron, reemplazo in _UNIDAD_DE_PRECIO:
        texto = re.sub(patron, reemplazo, texto)

    # Si algún campo llegó separado por coma (no por guion), se le pone la
    # preposición igual: "…, 2000 pesos" -> "… a 2000 pesos", sin la coma.
    texto = re.sub(r",\s*(\d[\d ]*\s*pesos)", r" a \1", texto)

    return texto


def preparar_para_voz(texto: str) -> str:
    """Convierte un mensaje escrito en uno que suene natural al pronunciarse.

    El orden importa: primero se quitan los enlaces (traen dígitos que si no
    se dictarían), después los números y al final las unidades.
    """
    # Las viñetas se numeran de PRIMERAS: el filtro de emojis se las lleva por
    # delante, y una vez borradas ya no se sabe dónde empieza cada oferta.
    texto = _enumerar_vinetas(texto)

    # Un enlace no se puede dictar; el dato útil ya va en el mensaje escrito.
    texto = _URL.sub("", texto)
    texto = _EMOJI.sub(" ", texto)

    # Los guiones entre campos se vuelven preposiciones, no comas: así la
    # oferta se dice de corrido en vez de a tirones. Va ANTES de expandir el
    # "$", que es la marca por la que se reconoce cuál campo es el precio.
    texto = unir_campos(texto)

    # "$2.000" -> "2000 pesos": el símbolo $ lo puede leer como "dólares".
    texto = re.sub(r"\$\s*(\d[\d.]*)", r"\1 pesos", texto)
    texto = _MILES.sub(_quitar_miles, texto)
    texto = _CELULAR.sub(_dictar_digitos, texto)

    for patron, reemplazo in _UNIDADES_HABLADAS:
        texto = re.sub(patron, reemplazo, texto)

    # Los saltos de línea se vuelven pausas habladas.
    texto = re.sub(r"\n+", ". ", texto)

    # Comillas y guiones de lista no aportan nada dichos en voz alta.
    texto = texto.replace('"', "").replace("—", ",")

    # "oferta(s)" se pronunciaría "oferta paréntesis ese": se deja el plural.
    texto = re.sub(r"\(s\)", "s", texto)

    texto = dar_fluidez(texto)

    # Limpieza final de la puntuación que dejaron los reemplazos. Va de última
    # a propósito: los pasos anteriores borran trozos y dejan huecos como
    # ". ." o ":." que solo se pueden juntar cuando ya nadie más va a tocar
    # el texto.
    texto = re.sub(r"\s+", " ", texto)
    texto = re.sub(r"\s+([,.;:!?])", r"\1", texto)
    texto = re.sub(r"[.,]\s*(?=[.,])", "", texto)   # ". ." y ", ," -> uno solo
    texto = re.sub(r":\s*\.", ":", texto)           # "ofertas:." -> "ofertas:"

    return re.sub(r"\s+", " ", texto).strip(" .,;:")


def texto_hablado(texto: str) -> str:
    """Pipeline completo: tono llanero + adaptación a voz.

    Es lo que se le pasa al sintetizador. Se aplica el tono ANTES de preparar
    la voz para que las sustituciones trabajen sobre el texto original, con su
    puntuación y mayúsculas intactas.
    """
    return preparar_para_voz(dar_tono_llanero(texto))
