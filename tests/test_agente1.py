"""Pruebas del Agente 1 (recepción/extracción) con el LLM mockeado.

No se hace ninguna llamada de red: se parchea `pedir_json` dentro del
módulo del agente. Cada test limpia `CONVERSACIONES` para no arrastrar
estado entre pruebas (el diccionario es un singleton a nivel de módulo).
"""
from datetime import datetime
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


@pytest.fixture(autouse=True)
def hora_fija_tarde():
    """Fija la hora en Colombia a la 1pm (mismo saludo en cada corrida de
    los tests, sin importar a qué hora se ejecute la suite)."""
    with patch.object(agente1, "datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 1, 1, 13, 0, tzinfo=agente1._HORA_COLOMBIA)
        yield


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
    assert oferta.pregunta_faltante == (
        "¡Buenas tardes! Perfecto, ya tengo anotado que ofreces 20 kg de plátano. "
        "¿Me podrías decir cuál es tu nombre?"
    )


def test_pregunta_por_telefono_cuando_falta():
    datos = {
        "producto": "plátano", "cantidad": 20, "unidad": "kg",
        "precio": 2000, "ubicacion": "Yopal", "nombre_productor": "Juan Pérez",
    }
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-3", "irrelevante")

    assert oferta.completo is False
    assert oferta.pregunta_faltante == (
        "¡Buenas tardes! Perfecto, ya tengo anotado que ofreces 20 kg de plátano. "
        "¿Me podrías decir a qué número de teléfono o WhatsApp te pueden contactar "
        "los compradores?"
    )


def test_acumula_datos_entre_turnos():
    """El productor manda la oferta en dos mensajes; el segundo turno debe
    completarla usando lo que ya se sabía del primero."""
    with _mock_llm(producto="plátano", cantidad=20, unidad="kg", precio=2000, ubicacion="Yopal"):
        primero = procesar_mensaje_productor("chat-4", "Tengo 20 kg de plátano a 2000 en Yopal")
    assert primero.completo is False
    assert primero.pregunta_faltante == (
        "¡Buenas tardes! Perfecto, ya tengo anotado que ofreces 20 kg de plátano. "
        "¿Me podrías decir cuál es tu nombre y a qué número de teléfono o "
        "WhatsApp te pueden contactar los compradores?"
    )

    with _mock_llm(nombre_productor="Juan Pérez", telefono_contacto="3001234567"):
        segundo = procesar_mensaje_productor("chat-4", "Me llamo Juan Pérez, mi número es 3001234567")

    assert segundo.completo is True
    assert segundo.producto == "plátano"  # se conservó del primer turno
    assert segundo.nombre_productor == "Juan Pérez"
    assert segundo.telefono_contacto == "3001234567"


def test_segundo_turno_no_repite_el_saludo():
    """En turnos posteriores al primero no se vuelve a saludar (sería
    repetitivo/poco natural), pero sí se sigue reconociendo lo ya sabido."""
    with _mock_llm(producto="papa", cantidad=4, unidad="kg"):
        primero = procesar_mensaje_productor("chat-7", "Tengo 4 kilos de papa")
    assert primero.completo is False
    assert primero.pregunta_faltante.startswith("¡Buenas tardes!")

    with _mock_llm(precio=1500):
        segundo = procesar_mensaje_productor("chat-7", "A 1500 el kilo")

    assert segundo.completo is False
    assert segundo.pregunta_faltante == (
        "¡Gracias! Ya tengo anotado que ofreces 4 kg de papa. "
        "¿Me podrías decir desde qué vereda o municipio lo ofreces, cuál es "
        "tu nombre y a qué número de teléfono o WhatsApp te pueden contactar "
        "los compradores?"
    )


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
    # Sin nada extraído, se saluda y se pregunta por los 6 campos obligatorios juntos.
    assert oferta.pregunta_faltante == (
        "¡Buenas tardes! Con gusto te ayudo a publicar tu oferta. "
        "¿Me podrías decir qué producto ofreces, qué cantidad tienes disponible "
        "(por ejemplo, 20 kg o 5 arrobas), a qué precio lo vendes, desde qué "
        "vereda o municipio lo ofreces, cuál es tu nombre y a qué número de "
        "teléfono o WhatsApp te pueden contactar los compradores?"
    )
