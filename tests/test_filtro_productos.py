"""Pruebas del filtro de dominio de productos (campo casanareño).

El LLM se mockea: se prueban las tres capas (tabla conocida, rechazo
evidente, LLM) y el comportamiento ante una caída del modelo.
"""
from unittest.mock import patch

import pytest

from agroia.agents import filtro_productos
from agroia.agents.filtro_productos import es_producto_del_campo, motivo_si_no_es_del_campo
from agroia.integrations.llm_client import LLMError


def _llm(es_del_campo: bool):
    return patch.object(
        filtro_productos, "pedir_json", return_value={"es_del_campo": es_del_campo}
    )


def _llm_no_debe_llamarse():
    """El LLM no debería consultarse: la respuesta sale de tabla o lista."""
    return patch.object(filtro_productos, "pedir_json", side_effect=AssertionError("no llamar"))


# --------------------------------------------------------------------------
# Capa 1: tabla de productos conocidos (sin LLM)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "producto",
    [
        "plátano", "PLATANOS", "yuca", "arroz", "maíz", "café", "cacao",
        "panela", "naranja", "tomate", "papa", "ñame", "aguacate",
        # Pecuarios y derivados: los que el mercado sí acepta.
        "leche", "huevos", "huevo", "queso", "cuajada", "carne", "res",
        "pollo", "miel",
    ],
)
def test_acepta_productos_conocidos_sin_consultar_al_llm(producto):
    with _llm_no_debe_llamarse():
        assert es_producto_del_campo(producto) is True


# --------------------------------------------------------------------------
# Capa 2: rechazo evidente (sin LLM)
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "producto",
    [
        "computador", "computadores", "celular", "televisor", "PlayStation",
        "portatil", "moto", "carro", "ropa", "zapatos",
        "vibrador", "vibradores", "condones", "marihuana", "pistola",
    ],
)
def test_rechaza_lo_evidente_sin_consultar_al_llm(producto):
    """Debe funcionar incluso con el LLM caído: es la capa que atrapa lo peor."""
    with _llm_no_debe_llamarse():
        assert es_producto_del_campo(producto) is False


def test_el_rechazo_es_por_palabra_completa():
    """'cerdo' no debe dispararse por parecerse a otra palabra de la lista."""
    with _llm(True):
        assert es_producto_del_campo("cerdo") is True


@pytest.mark.parametrize(
    "plural",
    ["computadores", "celulares", "televisores", "motos", "condones", "pastillas"],
)
def test_rechaza_tambien_los_plurales(plural):
    """La lista va en singular; los plurales los resuelve `_formas`. Sin esto,
    olvidar una variante dejaría pasar justo lo que se quiere bloquear."""
    with _llm_no_debe_llamarse():
        assert es_producto_del_campo(plural) is False


# --------------------------------------------------------------------------
# Capa 3: LLM para la cola larga
# --------------------------------------------------------------------------

def test_producto_raro_pero_del_campo_lo_decide_el_llm():
    with _llm(True):
        assert es_producto_del_campo("cachama") is True


def test_producto_raro_fuera_de_dominio_lo_decide_el_llm():
    with _llm(False):
        assert es_producto_del_campo("licencia de software") is False


# --------------------------------------------------------------------------
# Degradación
# --------------------------------------------------------------------------

def test_llm_caido_acepta_lo_desconocido():
    """Un cultivo poco común no debe quedar bloqueado por una falla nuestra."""
    with patch.object(filtro_productos, "pedir_json", side_effect=LLMError("timeout")):
        assert es_producto_del_campo("sacha inchi") is True


def test_llm_caido_sigue_rechazando_lo_evidente():
    """La capa 2 no depende del modelo: lo peor se sigue atajando."""
    with patch.object(filtro_productos, "pedir_json", side_effect=LLMError("timeout")):
        assert es_producto_del_campo("vibrador") is False


def test_respuesta_rara_del_llm_no_revienta():
    with patch.object(filtro_productos, "pedir_json", return_value={"otra_cosa": 1}):
        assert es_producto_del_campo("algo") is True


@pytest.mark.parametrize("vacio", ["", "   ", None])
def test_producto_vacio_no_se_acepta(vacio):
    with _llm_no_debe_llamarse():
        assert es_producto_del_campo(vacio) is False


# --------------------------------------------------------------------------
# Motivo legible
# --------------------------------------------------------------------------

def test_motivo_es_none_cuando_el_producto_sirve():
    with _llm_no_debe_llamarse():
        assert motivo_si_no_es_del_campo("plátano") is None


def test_motivo_nombra_el_producto_y_explica_el_mercado():
    with _llm_no_debe_llamarse():
        motivo = motivo_si_no_es_del_campo("computador")

    assert motivo is not None
    assert "computador" in motivo
    assert "campo casanareño" in motivo
