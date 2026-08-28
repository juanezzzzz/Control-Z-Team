"""Utilidades de texto compartidas por los agentes.

- `extraer_json`: parsea la respuesta del modelo de forma tolerante (a veces
  agrega texto antes/después del JSON pese al system prompt).
- `normalizar`: minúsculas + sin tildes + sin puntuación, para comparar
  términos de búsqueda de forma laxa contra lo que hay en la base de datos.
"""
import json
import re
import unicodedata
from typing import Any

_BLOQUE_JSON = re.compile(r"\{.*\}", re.DOTALL)


def extraer_json(texto: str) -> dict[str, Any]:
    """Devuelve el primer objeto JSON encontrado en `texto`.

    Lanza `ValueError` si no hay ningún objeto JSON válido — el llamador
    decide el fallback (nunca revienta con un `IndexError`/`JSONDecodeError`
    crudo).
    """
    if not texto:
        raise ValueError("respuesta vacía del modelo")

    texto = texto.strip()

    # Caso feliz: el texto ya es JSON puro.
    try:
        data = json.loads(texto)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: buscar el bloque {...} más externo.
    match = _BLOQUE_JSON.search(texto)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"no se encontró un objeto JSON en: {texto[:200]!r}")


def normalizar(texto: str | None) -> str:
    """Minúsculas, sin tildes, sin signos de puntuación y sin espacios
    sobrantes. Pensada para comparar términos de búsqueda de forma laxa
    (`"¿Alguien vende queso?"` -> `"alguien vende queso"`)."""
    if not texto:
        return ""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    # Todo lo que no sea letra/dígito/espacio se vuelve espacio.
    limpio = re.sub(r"[^\w\s]", " ", sin_tildes, flags=re.UNICODE)
    return re.sub(r"\s+", " ", limpio).strip().lower()
