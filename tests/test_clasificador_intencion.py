"""Pruebas del clasificador de intención (compra / venta / desconocida).

El LLM se mockea: se prueba el contrato del módulo (qué hace con cada
respuesta del modelo) y el respaldo por palabras clave.
"""
from unittest.mock import patch

import pytest

from agroia.agents import clasificador_intencion as clasificador
from agroia.agents.clasificador_intencion import (
    COMPRA,
    DESCONOCIDA,
    VENTA,
    _clasificar_por_palabras,
    clasificar_intencion,
)
from agroia.integrations.llm_client import LLMError


def _mock_llm(intencion: str):
    return patch.object(clasificador, "pedir_json", return_value={"intencion": intencion})


@pytest.mark.parametrize("intencion", [COMPRA, VENTA, DESCONOCIDA])
def test_devuelve_lo_que_dice_el_llm(intencion):
    with _mock_llm(intencion):
        assert clasificar_intencion("cualquier cosa") == intencion


def test_respuesta_invalida_del_llm_cae_a_palabras_clave():
    with _mock_llm("comprar_algo_raro"):
        assert clasificar_intencion("busco plátano") == COMPRA


def test_llm_caido_cae_a_palabras_clave():
    with patch.object(clasificador, "pedir_json", side_effect=LLMError("timeout")):
        assert clasificar_intencion("vendo 20 kg de papa") == VENTA


def test_llm_caido_y_sin_palabras_clave_devuelve_desconocida():
    """Lo importante: ante la duda NO se asume venta (el bug original)."""
    with patch.object(clasificador, "pedir_json", side_effect=LLMError("timeout")):
        assert clasificar_intencion("hola") == DESCONOCIDA


# --------------------------------------------------------------------------
# Respaldo por palabras clave (sin LLM)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mensaje",
    [
        "Busco plátano por Yopal",
        "necesito leche cerca de Aguazul",
        "Estoy buscando yuca",
        "quiero comprar maíz",
        "¿cuánto vale la papa?",
        "¿me vendes queso?",
        "¿quién tiene yuca?",
    ],
)
def test_palabras_clave_detectan_compra(mensaje):
    assert _clasificar_por_palabras(mensaje) == COMPRA


@pytest.mark.parametrize(
    "mensaje",
    [
        "Vendo 20 kilos de plátano a 2000 pesos",
        "Tengo leche disponible en Yopal",
        "Ofrezco yuca fresca",
        "quiero vender mi cosecha de café",
        "quiero publicar una oferta",
    ],
)
def test_palabras_clave_detectan_venta(mensaje):
    assert _clasificar_por_palabras(mensaje) == VENTA


@pytest.mark.parametrize(
    "mensaje",
    ["hola", "buenas", "gracias", "¿qué haces?", "ayuda", "50 arrobas de arroz"],
)
def test_palabras_clave_ante_la_duda_devuelven_desconocida(mensaje):
    assert _clasificar_por_palabras(mensaje) == DESCONOCIDA
