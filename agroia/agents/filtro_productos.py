"""Filtro de dominio: decide si un producto pertenece al campo casanareño.

AgroIA es un mercado agropecuario, no un clasificado general. Sin este filtro
cualquiera podría publicar un computador —o algo mucho peor— en un catálogo
que van a ver campesinos y compradores de la región.

Estrategia en tres capas, de la más barata a la más cara:

 1. Tabla conocida (`normalizacion._SINONIMOS_PRODUCTO`): si ya sabemos que
    es del campo, se acepta sin consultar al LLM. Cubre el caso común.
 2. Lista de rechazo obvio: electrónica, contenido para adultos, armas… Sirve
    para atajar lo evidente incluso si el LLM está caído.
 3. LLM: para la cola larga ("cachama", "sacha inchi", "morrocoy"), que ni
    una tabla ni una lista de palabras pueden cubrir.

Ante una caída del LLM se ACEPTA el producto desconocido. Es deliberado: un
campesino con un cultivo poco común no debería quedar bloqueado por una falla
nuestra, y lo evidentemente inaceptable ya lo atrapó la capa 2.
"""
import logging

from agroia.agents.normalizacion import es_producto_conocido
from agroia.core.text_utils import normalizar
from agroia.integrations.llm_client import LLMError, pedir_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el filtro de admisión de AgroIA Casanare, un mercado
para que los campesinos de Casanare (Colombia) vendan lo que producen.

Te paso el nombre de un producto y decidís si se puede publicar.

Respondé ÚNICAMENTE con un objeto JSON válido, sin texto adicional:
{ "es_del_campo": true | false }

Poné true si es algo que se produce, cultiva, cría o elabora en una finca o
vereda. Incluye:
- Cultivos y cosechas: plátano, yuca, arroz, maíz, café, cacao, frutas,
  hortalizas, tubérculos, forrajes, semillas, plántulas.
- Ganadería y derivados: ganado en pie, carne, leche, queso, cuajada, huevos,
  pollo, cerdo, miel, pescado de cultivo (cachama, tilapia).
- Productos elaborados en finca: panela, quesos artesanales, conservas,
  harinas, sal de la región.
- Insumos y elementos propios del trabajo agropecuario: abono, semilla,
  cabuya, guadua, madera de la finca.

Poné false si NO tiene que ver con el campo. Por ejemplo:
- Electrónica y electrodomésticos: computador, celular, televisor, consola.
- Vehículos, repuestos, ropa, muebles, servicios.
- Contenido o artículos para adultos, drogas, armas, medicamentos.
- Cualquier cosa ofensiva, ilegal, o sin relación con la producción rural.

Ante la duda con algo que suene rural o agropecuario, poné true.
"""

# Capa 2: lo que se rechaza aunque el LLM no esté disponible. Se compara por
# palabra completa contra el texto normalizado (sin tildes, en minúscula),
# para que "cerdo" no dispare por parecerse a otra palabra de la lista.
#
# Van en SINGULAR: `_formas()` se encarga de los plurales, así no hay que
# recordar agregar cada variante (y olvidar "computadores" dejaría pasar
# justo lo que se quiere bloquear).
_RECHAZO_EVIDENTE = frozenset({
    # electrónica y afines
    "computador", "computadora", "pc", "portatil", "laptop", "celular",
    "telefono", "smartphone", "iphone", "tablet", "televisor", "tv",
    "consola", "playstation", "xbox", "audifono", "parlante", "camara",
    "impresora", "monitor", "teclado", "mouse", "drone", "dron",
    # vehículos y repuestos
    "carro", "moto", "motocicleta", "bicicleta", "llanta", "bateria", "motor",
    # adultos / ilegal
    "vibrador", "consolador", "sexual", "porno", "pornografia", "condon",
    "droga", "cocaina", "marihuana", "arma", "pistola", "revolver", "municion",
    # otros claramente fuera de dominio
    "ropa", "zapato", "mueble", "joya", "reloj", "perfume", "medicamento",
    "pastilla",
})


def _formas(palabra: str) -> set[str]:
    """La palabra y su singular probable: 'computadores' -> {'computadores',
    'computadore', 'computador'}. Basta para plurales del español sin meter
    un lematizador."""
    formas = {palabra}
    if palabra.endswith("es") and len(palabra) > 3:
        formas.add(palabra[:-2])
    if palabra.endswith("s") and len(palabra) > 2:
        formas.add(palabra[:-1])
    return formas

MOTIVO_RECHAZO = (
    "no puedo publicar «{producto}» porque AgroIA es un mercado del campo "
    "casanareño: cosechas, frutas, verduras, ganado, leche, queso, huevos, "
    "carne, miel y demás productos de la finca"
)


def _rechazo_evidente(producto: str) -> bool:
    return any(
        _formas(palabra) & _RECHAZO_EVIDENTE
        for palabra in normalizar(producto).split()
    )


def es_producto_del_campo(producto: str) -> bool:
    """¿Se puede publicar este producto? Nunca lanza excepción."""
    texto = (producto or "").strip()
    if not texto:
        return False

    # 1. Ya está en la tabla de productos del campo: no hay nada que decidir.
    if es_producto_conocido(texto):
        return True

    # 2. Evidentemente fuera de dominio: no se gasta una llamada al LLM.
    if _rechazo_evidente(texto):
        return False

    # 3. Cola larga: que decida el modelo.
    try:
        datos = pedir_json(SYSTEM_PROMPT, texto)
    except LLMError:
        # Falla nuestra, no del campesino: se acepta. Lo evidentemente
        # inaceptable ya se filtró arriba.
        logger.warning("Filtro de productos: LLM caído, acepto %r", texto, exc_info=True)
        return True

    valor = datos.get("es_del_campo")
    if isinstance(valor, bool):
        return valor
    logger.warning("Filtro de productos: respuesta rara del LLM para %r: %r", texto, datos)
    return True


def motivo_si_no_es_del_campo(producto: str) -> str | None:
    """Devuelve el motivo (redactado para una persona) si el producto no se
    puede publicar, o None si sí se puede."""
    if es_producto_del_campo(producto):
        return None
    return MOTIVO_RECHAZO.format(producto=(producto or "").strip())
