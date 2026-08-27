"""Pruebas del Agente 3 (ventas) con Gemini y Supabase mockeados.

No se hace ninguna llamada de red: se parchea `_extraer_con_gemini` (Gemini)
y `buscar_productos` (repositorio) dentro del módulo del agente.
"""
from unittest.mock import patch

import pytest

from agroia.agents import agente3_ventas
from agroia.agents.agente3_ventas import atender_consulta_comprador

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
def gemini_ok():
    """Gemini extrae {producto: plátano, ubicacion: Yopal}."""
    with patch.object(
        agente3_ventas,
        "_extraer_con_gemini",
        return_value={"producto": "plátano", "ubicacion": "Yopal"},
    ) as m:
        yield m


def test_flujo_feliz_con_resultados(gemini_ok):
    with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_PLATANO]) as buscar:
        out = atender_consulta_comprador("Busco plátano por Yopal")

    buscar.assert_called_once_with(producto="plátano", ubicacion="Yopal")
    assert len(out.resultados) == 1
    assert out.resultados[0].producto == "plátano hartón"
    assert "Plátano Hartón" in out.respuesta_texto
    assert "$2,000" in out.respuesta_texto
    assert "wa.me/573001112233" in out.respuesta_texto


def test_sin_resultados(gemini_ok):
    with patch.object(agente3_ventas, "buscar_productos", return_value=[]):
        out = atender_consulta_comprador("Busco caviar por Yopal")

    assert out.resultados == []
    assert "no encontré" in out.respuesta_texto.lower()


def test_contacto_no_disponible():
    with patch.object(
        agente3_ventas, "_extraer_con_gemini", return_value={"producto": "leche", "ubicacion": None}
    ):
        with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_LECHE]):
            out = atender_consulta_comprador("Necesito leche")

    assert "contacto no disponible" in out.respuesta_texto.lower()


def test_interpretar_intencion_solo_producto():
    """Gemini da producto pero no ubicación: NO se dispara la heurística."""
    with patch.object(
        agente3_ventas, "_extraer_con_gemini", return_value={"producto": "leche", "ubicacion": None}
    ):
        assert agente3_ventas._interpretar_intencion("necesito leche") == {
            "producto": "leche",
            "ubicacion": None,
        }


def test_gemini_no_llama_herramienta_usa_heuristica():
    """Gemini no devuelve function_call -> {} -> heurística sobre el texto crudo."""
    with patch.object(agente3_ventas, "_extraer_con_gemini", return_value={}):
        with patch.object(agente3_ventas, "buscar_productos", return_value=[FILA_PLATANO]) as buscar:
            out = atender_consulta_comprador("busco plátano en Yopal")

    # "busco", "en" son relleno -> término esperado: "platano yopal"
    _, kwargs = buscar.call_args
    assert kwargs["producto"] == "platano yopal"
    assert kwargs["ubicacion"] is None
    assert len(out.resultados) == 1


def test_gemini_lanza_excepcion_no_revienta():
    with patch.object(agente3_ventas, "_extraer_con_gemini", side_effect=RuntimeError("API caída")):
        with patch.object(agente3_ventas, "buscar_productos", return_value=[]) as buscar:
            out = atender_consulta_comprador("busco yuca")

    buscar.assert_called_once()
    assert isinstance(out.respuesta_texto, str)
    assert out.resultados == []


def test_busqueda_falla_devuelve_mensaje_amable(gemini_ok):
    with patch.object(agente3_ventas, "buscar_productos", side_effect=RuntimeError("Supabase 500")):
        out = atender_consulta_comprador("Busco plátano por Yopal")

    assert out.resultados == []
    assert "problema" in out.respuesta_texto.lower()


def test_ordena_por_coincidencia_de_ubicacion():
    """Con ubicación 'Aguazul', la fila de Aguazul debe quedar primero."""
    fila_yopal = {**FILA_PLATANO, "ubicacion": "Yopal"}
    fila_aguazul = {**FILA_LECHE, "ubicacion": "Aguazul"}
    with patch.object(
        agente3_ventas, "_extraer_con_gemini", return_value={"producto": None, "ubicacion": "Aguazul"}
    ):
        with patch.object(
            agente3_ventas, "buscar_productos", return_value=[fila_yopal, fila_aguazul]
        ):
            out = atender_consulta_comprador("¿Qué hay cerca de Aguazul?")

    assert out.resultados[0].ubicacion == "Aguazul"
