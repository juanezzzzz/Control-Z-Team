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
_ORDINALES = ("La primera:", "La segunda:", "La tercera:", "La cuarta:", "La quinta:")

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
        etiqueta = _ORDINALES[i] if i < len(_ORDINALES) else "Y otra:"
        resultado.append(f" {etiqueta}{parte.rstrip()}")

    return "".join(resultado)


def dar_fluidez(texto: str) -> str:
    """Retoques de ritmo para que no suene a texto leído por una máquina.

    Un sintetizador neuronal saca su entonación de la puntuación y de la
    gramática: una frase bien puntuada y bien construida ya suena natural,
    mientras que un renglón corrido, sin comas y con concordancias raras
    ("por kilos") delata a la máquina por más que se le baje la velocidad.
    """
    for patron, reemplazo in _UNIDAD_DE_PRECIO:
        texto = re.sub(patron, reemplazo, texto)

    # "…, 2000 pesos, Yopal" -> "…, a 2000 pesos, en Yopal": las preposiciones
    # son las que convierten una lista de campos en una frase.
    texto = re.sub(r",\s*(\d[\d ]*\s*pesos)", r", a \1", texto)

    # Una coma antes del cierre le da el respiro que haría una persona.
    texto = re.sub(r"\s+(ya pueden|ya puede)\b", r", \1", texto)

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
    # El guion entre campos ("Plátano - 20 kilos - Yopal") suena mejor como pausa.
    texto = re.sub(r"\s+-\s+", ", ", texto)

    # Con los campos ya separados por comas se puede armar la frase: acá es
    # donde "2000 pesos, Yopal" se vuelve "a 2000 pesos, en Yopal".
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
