"""Tablas y funciones de estandarización que usa el Agente 2.

Viven aparte del agente, y sin ningún I/O, por dos razones:

 1. Son la parte que más se toca cuando aparece un producto, una unidad o
    un municipio nuevo — conviene tenerlas todas en un solo archivo.
 2. Se pueden probar sin Supabase ni Gemini (ver tests/test_agente2.py).

Criterio general: cuando un valor no está en las tablas, se devuelve
limpio pero SIN inventarle una forma canónica. Es preferible guardar lo
que escribió el campesino que corromper un dato que no conocemos.
"""
import re
import unicodedata
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Utilidades de texto
# ---------------------------------------------------------------------------

def sin_acentos(texto: str) -> str:
    """'Plátano' -> 'platano'. Solo se usa para CONSTRUIR CLAVES de búsqueda;
    el valor que se termina guardando conserva los acentos correctos."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _clave(texto: str) -> str:
    """Forma con la que se busca en los diccionarios de abajo: sin acentos,
    en minúscula y con los espacios colapsados."""
    return " ".join(sin_acentos(texto).lower().split())


# ---------------------------------------------------------------------------
# Unidades de medida
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Unidad:
    """Una unidad de medida ya estandarizada.

    `factor_base` es a cuántas unidades base equivale 1 de esta unidad
    (1 arroba = 12.5 kg). Es None cuando la equivalencia NO es fija en el
    campo — un bulto o un racimo no pesan siempre lo mismo — y en ese caso
    el Agente 2 se abstiene de calcular los campos derivados en vez de
    publicar una conversión inventada.
    """

    canonica: str
    categoria: str          # "peso" | "volumen" | "conteo"
    base: str               # "kg" | "L" | "unidad"
    factor_base: float | None


_UNIDADES: tuple[Unidad, ...] = (
    # Peso — base kg
    Unidad("kg", "peso", "kg", 1.0),
    Unidad("g", "peso", "kg", 0.001),
    Unidad("lb", "peso", "kg", 0.5),           # la libra colombiana son 500 g
    Unidad("arroba", "peso", "kg", 12.5),      # arroba colombiana
    Unidad("carga", "peso", "kg", 125.0),      # 10 arrobas
    Unidad("tonelada", "peso", "kg", 1000.0),
    Unidad("bulto", "peso", "kg", None),       # varía según el producto
    # Volumen — base L
    Unidad("L", "volumen", "L", 1.0),
    Unidad("ml", "volumen", "L", 0.001),
    Unidad("galón", "volumen", "L", 3.785),
    # Conteo — base unidad
    Unidad("unidad", "conteo", "unidad", 1.0),
    Unidad("docena", "conteo", "unidad", 12.0),
    Unidad("racimo", "conteo", "unidad", None),
    Unidad("atado", "conteo", "unidad", None),
    Unidad("canasta", "conteo", "unidad", None),
    Unidad("caja", "conteo", "unidad", None),
)

_POR_CANONICA: dict[str, Unidad] = {u.canonica: u for u in _UNIDADES}

# Todo lo que un campesino puede escribir -> unidad canónica.
_SINONIMOS_UNIDAD: dict[str, str] = {
    # peso
    "kg": "kg", "kgs": "kg", "k": "kg",
    "kilo": "kg", "kilos": "kg", "kilogramo": "kg", "kilogramos": "kg",
    "g": "g", "gr": "g", "grs": "g", "gramo": "g", "gramos": "g",
    "lb": "lb", "lbs": "lb", "libra": "lb", "libras": "lb",
    "@": "arroba", "arroba": "arroba", "arrobas": "arroba",
    "carga": "carga", "cargas": "carga",
    "t": "tonelada", "ton": "tonelada",
    "tonelada": "tonelada", "toneladas": "tonelada",
    "bulto": "bulto", "bultos": "bulto", "costal": "bulto", "costales": "bulto",
    # volumen
    "l": "L", "lt": "L", "lts": "L", "litro": "L", "litros": "L",
    "ml": "ml", "mililitro": "ml", "mililitros": "ml",
    "gl": "galón", "galon": "galón", "galones": "galón",
    # conteo
    "u": "unidad", "un": "unidad", "und": "unidad", "unds": "unidad",
    "unid": "unidad", "unidad": "unidad", "unidades": "unidad",
    "doc": "docena", "docena": "docena", "docenas": "docena",
    "racimo": "racimo", "racimos": "racimo",
    "atado": "atado", "atados": "atado", "manojo": "atado", "manojos": "atado",
    "canasta": "canasta", "canastas": "canasta",
    "caja": "caja", "cajas": "caja",
}


def normalizar_unidad(unidad: str | None) -> Unidad | None:
    """'arrobas' -> Unidad(canonica='arroba', base='kg', factor_base=12.5).

    Devuelve None si la unidad viene vacía o no está en la tabla; el Agente 2
    guarda entonces el texto original tal cual, sin conversión.
    """
    if not unidad:
        return None

    clave = _clave(unidad)
    canonica = _SINONIMOS_UNIDAD.get(clave)
    if canonica is None:
        # "20 kg." o "kilos:" — reintenta sin la puntuación pegada
        canonica = _SINONIMOS_UNIDAD.get(clave.strip(".,;:()"))
    if canonica is None:
        return None
    return _POR_CANONICA[canonica]


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

# Solo lo más frecuente en Casanare; ampliar esta tabla es el cambio típico
# cuando aparece un producto nuevo. Las claves van sin acentos y en minúscula
# porque la búsqueda se hace con _clave().
_SINONIMOS_PRODUCTO: dict[str, str] = {
    "platano": "plátano", "platanos": "plátano",
    "yuca": "yuca", "yucas": "yuca",
    "arroz": "arroz", "arroces": "arroz",
    "maiz": "maíz", "maices": "maíz", "mais": "maíz",
    "cafe": "café", "cafes": "café",
    "cacao": "cacao",
    "panela": "panela", "panelas": "panela",
    "leche": "leche", "leches": "leche",
    "queso": "queso", "quesos": "queso",
    "cuajada": "cuajada", "cuajadas": "cuajada",
    "huevo": "huevo", "huevos": "huevo",
    "pollo": "pollo", "pollos": "pollo",
    "carne": "carne de res", "carne de res": "carne de res", "res": "carne de res",
    "miel": "miel", "mieles": "miel",
    "naranja": "naranja", "naranjas": "naranja",
    "limon": "limón", "limones": "limón",
    "mango": "mango", "mangos": "mango",
    "pina": "piña", "pinas": "piña",          # "piña"/"piñas" pierden la ñ en _clave()
    "papaya": "papaya", "papayas": "papaya",
    "guayaba": "guayaba", "guayabas": "guayaba",
    "patilla": "patilla", "patillas": "patilla",
    "sandia": "patilla", "sandias": "patilla",  # en los Llanos se dice patilla
    "aguacate": "aguacate", "aguacates": "aguacate",
    "tomate": "tomate", "tomates": "tomate",
    "cebolla": "cebolla", "cebollas": "cebolla",
    "papa": "papa", "papas": "papa",
    "ahuyama": "ahuyama", "ahuyamas": "ahuyama",
    "auyama": "ahuyama", "auyamas": "ahuyama",
    "name": "ñame", "names": "ñame",           # "ñame" pierde la ñ en _clave()
    "arracacha": "arracacha", "arracachas": "arracacha",
    "frijol": "fríjol", "frijoles": "fríjol", "frisol": "fríjol",
    "sorgo": "sorgo",
    "soya": "soya",
}


def normalizar_producto(producto: str) -> str:
    """'  PLATANOS ' -> 'plátano'.

    Si el producto no está en el diccionario se devuelve limpio (minúscula,
    sin espacios de más) pero sin acentuarlo ni singularizarlo por nuestra
    cuenta: el Agente 3 busca con ilike, así que un nombre poco común sigue
    siendo encontrable.
    """
    limpio = " ".join(producto.split()).lower()
    return _SINONIMOS_PRODUCTO.get(_clave(limpio), limpio)


# ---------------------------------------------------------------------------
# Ubicación
# ---------------------------------------------------------------------------

MUNICIPIOS_CASANARE: tuple[str, ...] = (
    "Yopal", "Aguazul", "Chámeza", "Hato Corozal", "La Salina", "Maní",
    "Monterrey", "Nunchía", "Orocué", "Paz de Ariporo", "Pore", "Recetor",
    "Sabanalarga", "Sácama", "San Luis de Palenque", "Támara", "Tauramena",
    "Trinidad", "Villanueva",
)

_MUNICIPIOS_POR_CLAVE: dict[str, str] = {_clave(m): m for m in MUNICIPIOS_CASANARE}

# Conectores que van en minúscula dentro de un topónimo.
_CONECTORES = {"de", "del", "y"}
# Los artículos SÍ se capitalizan cuando son parte del nombre ("La Salina",
# "Vereda El Charte"); solo bajan a minúscula detrás de un conector
# ("Puerto de la Cruz").
_ARTICULOS = {"el", "la", "los", "las"}


def _titulo_es(texto: str) -> str:
    """.title() con reglas del español: 'san luis de palenque' ->
    'San Luis de Palenque' (str.title() daría 'San Luis De Palenque'), pero
    'vereda el charte' -> 'Vereda El Charte'."""
    palabras = texto.split()
    resultado: list[str] = []

    for i, palabra in enumerate(palabras):
        minuscula = palabra.lower()
        anterior = palabras[i - 1].lower().strip(",") if i else ""

        if i == 0:
            resultado.append(palabra.capitalize())
        elif minuscula in _CONECTORES:
            resultado.append(minuscula)
        elif minuscula in _ARTICULOS and anterior in _CONECTORES:
            resultado.append(minuscula)
        else:
            resultado.append(palabra.capitalize())

    return " ".join(resultado)


def normalizar_ubicacion(ubicacion: str) -> tuple[str, str | None]:
    """Devuelve (ubicacion_presentable, municipio_reconocido).

    `municipio` sale no-nulo solo si el texto corresponde a uno de los 19
    municipios de Casanare — sea porque la ubicación entera es el municipio
    ("yopal") o porque lo menciona ("Vereda El Charte, Yopal"). Para una
    vereda que no lo menciona se devuelve None y el filtro por municipio
    del catálogo simplemente no la incluye, pero la búsqueda por texto del
    Agente 3 la sigue encontrando.
    """
    limpio = " ".join(ubicacion.split())
    clave = _clave(limpio)

    municipio = _MUNICIPIOS_POR_CLAVE.get(clave)
    if municipio:
        return municipio, municipio

    for clave_municipio, nombre in _MUNICIPIOS_POR_CLAVE.items():
        if re.search(rf"\b{re.escape(clave_municipio)}\b", clave):
            return _titulo_es(limpio), nombre

    return _titulo_es(limpio), None
