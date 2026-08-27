"""Pruebas del Agente 3 (ventas) con Claude y Supabase mockeados.

No se hace ninguna llamada de red: se parchea `_client` (Anthropic) y
`buscar_productos` (repositorio) dentro del módulo del agente.
"""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agroia.agents import agente3_ventas
from agroia.agents.agente3_ventas import atender_consulta_comprador


def _respuesta_claude(texto: str):
    """Imita anthropic.types.Message: resp.content[0].text."""
    return SimpleNamespace(content=[SimpleNamespace(text=texto)])


FILA_PLATANO = {
    "id": "11111111-1111-1111-1111-111111111111",
    "producto": "plátano hartón",
    "cantidad": 200,
    "unidad": "kg",
    "precio": 2000,
    "ubicacion": "Yopal",
    "telefono_contacto": "573001112233",
    "estado": "activo",
}
FILA_LECHE = {
    "id": "22222222-2222-2222-2222-222222222222",
    "producto": "leche",
    "cantidad": 80,
    "unidad": "litros",
    "precio": 2500,
    "ubicacion": "Aguazul",
    "telefono_contacto": None,
    "estado": "activo",
}


@pytest.fixture
def claude_ok():
    with patch.object(agente3_ventas, "_client") as cli:
        cli.messages.create.return_value = _respuesta_claude(
            '{"producto": "plátano", "ubicacion": "Yopal"}'
        )
        yield cli


def test_flujo_feliz_con_resultados(claude_ok):
    with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_PLATANO]) as buscar:
        out = atender_consulta_comprador("Busco plátano por Yopal")

    buscar.assert_called_once_with(producto="plátano", ubicacion="Yopal")
    assert len(out.resultados) == 1
    assert out.resultados[0].producto == "plátano hartón"
    assert "Plátano Hartón" in out.respuesta_texto
    assert "$2,000" in out.respuesta_texto
    assert "wa.me/573001112233" in out.respuesta_texto


def test_sin_resultados(claude_ok):
    with patch.object(agente3_ventas, "buscar_productos", return_value=[]):
        out = atender_consulta_comprador("Busco caviar por Yopal")

    assert out.resultados == []
    assert "no encontré" in out.respuesta_texto.lower()


def test_contacto_no_disponible(claude_ok):
    with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_LECHE]):
        out = atender_consulta_comprador("Necesito leche")

    assert "contacto no disponible" in out.respuesta_texto.lower()


def test_claude_devuelve_basura_usa_heuristica():
    """Si Claude no devuelve JSON, se busca con el texto limpio como producto."""
    with patch.object(agente3_ventas, "_client") as cli:
        cli.messages.create.return_value = _respuesta_claude("Mmm, no estoy seguro de qué buscas.")
        with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_PLATANO]) as buscar:
            out = atender_consulta_comprador("busco plátano en Yopal")

    # "busco", "en" son relleno -> término esperado: "platano yopal"
    _, kwargs = buscar.call_args
    assert kwargs["producto"] == "platano yopal"
    assert kwargs["ubicacion"] is None
    assert len(out.resultados) == 1


def test_claude_lanza_excepcion_no_revienta():
    with patch.object(agente3_ventas, "_client") as cli:
        cli.messages.create.side_effect = RuntimeError("API caída")
        with patch.object(agente3_ventas, "buscar_productos", return_value=[]) as buscar:
            out = atender_consulta_comprador("busco yuca")

    buscar.assert_called_once()
    assert isinstance(out.respuesta_texto, str)
    assert out.resultados == []


def test_busqueda_falla_devuelve_mensaje_amable(claude_ok):
    with patch.object(agente3_ventas, "buscar_productos", side_effect=RuntimeError("Supabase 500")):
        out = atender_consulta_comprador("Busco plátano por Yopal")

    assert out.resultados == []
    assert "problema" in out.respuesta_texto.lower()


def test_ordena_por_coincidencia_de_ubicacion():
    """Con ubicación 'Aguazul', la fila de Aguazul debe quedar primero."""
    fila_yopal = {**FILA_PLATANO, "ubicacion": "Yopal"}
    fila_aguazul = {**FILA_LECHE, "ubicacion": "Aguazul"}
    with patch.object(agente3_ventas, "_client") as cli:
        cli.messages.create.return_value = _respuesta_claude(
            '{"producto": null, "ubicacion": "Aguazul"}'
        )
        with patch.object(agente3_ventas, "buscar_productos", return_value=[fila_yopal, fila_aguazul]):
            out = atender_consulta_comprador("¿Qué hay cerca de Aguazul?")

    assert out.resultados[0].ubicacion == "Aguazul"
