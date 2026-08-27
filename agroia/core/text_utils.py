"""Utilidades de texto compartidas por los agentes.

- `normalizar`: minúsculas + sin tildes + sin puntuación, para comparar
  términos de búsqueda de forma laxa contra lo que hay en la base de datos.
"""
import re
import unicodedata


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
