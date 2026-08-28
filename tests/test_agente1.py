"""Pruebas del Agente 1 (recepción/extracción) con el LLM mockeado.

No se hace ninguna llamada de red: se parchea `pedir_json` dentro del
módulo del agente. Cada test limpia `CONVERSACIONES` para no arrastrar
estado entre pruebas (el diccionario es un singleton a nivel de módulo).
"""
from unittest.mock import patch

import pytest

from agroia.agents import agente1_recepcion as agente1
from agroia.agents.agente1_recepcion import procesar_mensaje_productor
from agroia.integrations.llm_client import LLMError


@pytest.fixture(autouse=True)
def limpiar_conversaciones():
    agente1.CONVERSACIONES.clear()
    yield
    agente1.CONVERSACIONES.clear()


def _mock_llm(**campos):
    """Devuelve un patcher de pedir_json que responde exactamente `campos`
    (los que falten quedan implícitamente ausentes del dict, como haría el
    LLM real al no mencionarlos)."""
    return patch.object(agente1, "pedir_json", return_value=campos)


def test_mensaje_completo_en_un_solo_turno():
    datos = {
        "producto": "plátano",
        "cantidad": 20,
        "unidad": "kg",
        "precio": 2000,
        "ubicacion": "Yopal",
        "nombre_productor": "Juan Pérez",
        "telefono_contacto": "3001234567",
    }
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-1", "irrelevante, el LLM está mockeado")

    assert oferta.completo is True
    assert oferta.pregunta_faltante is None
    assert oferta.nombre_productor == "Juan Pérez"
    assert oferta.telefono_contacto == "3001234567"


def test_pregunta_por_nombre_cuando_falta():
    datos = {
        "producto": "plátano", "cantidad": 20, "unidad": "kg",
        "precio": 2000, "ubicacion": "Yopal", "telefono_contacto": "3001234567",
    }
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-2", "Tengo 20 kg de plátano a 2000 en Yopal, mi cel es 3001234567")

    assert oferta.completo is False
    assert oferta.pregunta_faltante == "¿Cuál es tu nombre?"


def test_pregunta_por_telefono_cuando_falta():
    datos = {
        "producto": "plátano", "cantidad": 20, "unidad": "kg",
        "precio": 2000, "ubicacion": "Yopal", "nombre_productor": "Juan Pérez",
    }
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-3", "irrelevante")

    assert oferta.completo is False
    assert oferta.pregunta_faltante == "¿A qué número de teléfono o WhatsApp te pueden contactar los compradores?"


def test_acumula_datos_entre_turnos():
    """El productor manda la oferta en dos mensajes; el segundo turno debe
    completarla usando lo que ya se sabía del primero."""
    with _mock_llm(producto="plátano", cantidad=20, unidad="kg", precio=2000, ubicacion="Yopal"):
        primero = procesar_mensaje_productor("chat-4", "Tengo 20 kg de plátano a 2000 en Yopal")
    assert primero.completo is False

    with _mock_llm(nombre_productor="Juan Pérez", telefono_contacto="3001234567"):
        segundo = procesar_mensaje_productor("chat-4", "Me llamo Juan Pérez, mi número es 3001234567")

    assert segundo.completo is True
    assert segundo.producto == "plátano"  # se conservó del primer turno
    assert segundo.nombre_productor == "Juan Pérez"
    assert segundo.telefono_contacto == "3001234567"


def test_conversacion_se_limpia_al_completarse():
    datos = {
        "producto": "plátano", "cantidad": 20, "unidad": "kg", "precio": 2000,
        "ubicacion": "Yopal", "nombre_productor": "Juan", "telefono_contacto": "3001234567",
    }
    with _mock_llm(**datos):
        procesar_mensaje_productor("chat-5", "irrelevante")

    assert "chat-5" not in agente1.CONVERSACIONES


def test_llm_falla_no_revienta_y_vuelve_a_preguntar():
    with patch.object(agente1, "pedir_json", side_effect=LLMError("caída")):
        oferta = procesar_mensaje_productor("chat-6", "Tengo plátano")

    assert oferta.completo is False
    # Sin nada extraído, el primer campo obligatorio de la lista es "producto".
    assert oferta.pregunta_faltante == "¿Qué producto quieres ofrecer?"
