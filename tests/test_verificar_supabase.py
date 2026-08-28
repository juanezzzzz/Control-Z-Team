"""El verificador debe distinguir la clave anon de la service_role.

Es la comprobación que más tiempo ahorra: usar la anon key en el backend hace
que los inserts fallen devolviendo 0 filas, sin lanzar ningún error.
"""
import base64
import json

import pytest

from scripts.verificar_supabase import _rol_de_la_clave


def _jwt(rol: str) -> str:
    """JWT con la forma de una clave clásica de Supabase (firma inventada:
    el verificador lee el claim, no valida la firma)."""
    cabecera = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').decode().rstrip("=")
    carga = base64.urlsafe_b64encode(
        json.dumps({"iss": "supabase", "role": rol}).encode()
    ).decode().rstrip("=")
    return f"{cabecera}.{carga}.firma-inventada"


@pytest.mark.parametrize(
    "clave, rol_esperado",
    [
        (_jwt("anon"), "anon"),
        (_jwt("service_role"), "service_role"),
        ("sb_publishable_abc123", "anon"),        # formato nuevo de Supabase
        ("sb_secret_abc123", "service_role"),
        ("esto-no-es-una-clave", None),
        ("", None),
        ("a.b.c", None),                          # tres partes pero no es base64 válido
    ],
)
def test_identifica_el_rol_de_la_clave(clave, rol_esperado):
    assert _rol_de_la_clave(clave) == rol_esperado
