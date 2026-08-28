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


# --------------------------------------------------------------------------
# El modelo se hace el desentendido con productos fuera de dominio
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mensaje, esperado",
    [
        ("Vendo vibradores a 50000 en Yopal", VENTA),
        ("Vendo un computador gamer en Yopal", VENTA),
        ("Ofrezco un celular usado", VENTA),
        ("Busco un televisor", COMPRA),
        ("Necesito una moto", COMPRA),
    ],
)
def test_apertura_inequivoca_gana_sobre_un_desconocida_del_llm(mensaje, esperado):
    """El modelo a veces responde "desconocida" ante productos fuera de
    dominio, aunque la intención sea obvia. Mandar el menú ahí confunde: la
    persona dijo claramente que quería vender. Con la intención bien detectada,
    el filtro de productos puede explicarle por qué no se publica."""
    with _mock_llm(DESCONOCIDA):
        assert clasificar_intencion(mensaje) == esperado


@pytest.mark.parametrize(
    "mensaje",
    [
        "hola",
        "tengo una pregunta",     # "tengo" NO es apertura inequívoca
        "buenas, cómo funciona",
        "gracias",
    ],
)
def test_desconocida_del_llm_se_respeta_si_no_hay_apertura_clara(mensaje):
    with _mock_llm(DESCONOCIDA):
        assert clasificar_intencion(mensaje) == DESCONOCIDA


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
