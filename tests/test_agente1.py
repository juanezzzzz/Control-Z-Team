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
        "¿Me podrías decir cuál es tu nombre? "
        "Y si tienes un local o finca donde te puedan visitar, cuéntame la "
        "dirección para agregarla; si no, no hay problema."
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
        "los compradores? "
        "Y si tienes un local o finca donde te puedan visitar, cuéntame la "
        "dirección para agregarla; si no, no hay problema."
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
        "WhatsApp te pueden contactar los compradores? "
        "Y si tienes un local o finca donde te puedan visitar, cuéntame la "
        "dirección para agregarla; si no, no hay problema."
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
        "¿Me podrías decir desde qué municipio de Casanare lo ofreces (y la "
        "vereda, si aplica), cuál es tu nombre y a qué número de teléfono o "
        "WhatsApp te pueden contactar los compradores?"
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
        "municipio de Casanare lo ofreces (y la vereda, si aplica), cuál es tu "
        "nombre y a qué número de teléfono o WhatsApp te pueden contactar los "
        "compradores?"
    )


# --------------------------------------------------------------------------
# Validación de datos mal dados
# --------------------------------------------------------------------------

_OFERTA_SIN_TELEFONO = {
    "producto": "plátano", "cantidad": 20, "unidad": "kg",
    "precio": 2000, "ubicacion": "Yopal", "nombre_productor": "Juan Pérez",
}


@pytest.mark.parametrize(
    "telefono, fragmento_esperado",
    [
        ("12", "parece muy corto"),
        ("300123456789012345", "parece muy largo"),
        ("0000000000", "parece incompleto"),
        ("no tengo", "no tiene ningún dígito"),
    ],
)
def test_telefono_invalido_se_rechaza_con_disculpa(telefono, fragmento_esperado):
    """No se guarda un teléfono imposible: se pide de nuevo, explicando por qué."""
    with _mock_llm(**_OFERTA_SIN_TELEFONO, telefono_contacto=telefono):
        oferta = procesar_mensaje_productor("chat-tel", "irrelevante")

    assert oferta.completo is False
    assert oferta.telefono_contacto is None  # no se guardó el inválido
    assert oferta.pregunta_faltante.startswith("Disculpa,")
    assert fragmento_esperado in oferta.pregunta_faltante
    assert "¿Me podrías decir a qué número" in oferta.pregunta_faltante


@pytest.mark.parametrize("telefono", ["3001234567", "573001234567", "+57 300 123 4567", "6358080"])
def test_telefono_valido_se_acepta(telefono):
    with _mock_llm(**_OFERTA_SIN_TELEFONO, telefono_contacto=telefono):
        oferta = procesar_mensaje_productor("chat-tel-ok", "irrelevante")

    assert oferta.completo is True
    assert oferta.telefono_contacto == telefono


def test_precio_absurdo_se_rechaza_antes_de_publicar():
    datos = {**_OFERTA_SIN_TELEFONO, "telefono_contacto": "3001234567", "precio": 2_000_000_000}
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-precio", "a dos mil el kilo")

    assert oferta.completo is False
    assert "el precio que me diste" in oferta.pregunta_faltante
    assert "parece demasiado alto" in oferta.pregunta_faltante


def test_cantidad_cero_se_rechaza():
    datos = {**_OFERTA_SIN_TELEFONO, "telefono_contacto": "3001234567", "cantidad": 0}
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-cant", "irrelevante")

    assert oferta.completo is False
    assert "la cantidad debe ser mayor que cero" in oferta.pregunta_faltante


def test_correccion_invalida_no_pisa_el_dato_valido_anterior():
    """Turno 1 da un teléfono bueno; turno 2 intenta corregirlo con uno malo.
    El malo se rechaza, el bueno se conserva, y NO se publica en silencio:
    se le vuelve a preguntar para que confirme."""
    with _mock_llm(**_OFERTA_SIN_TELEFONO, telefono_contacto="3001234567"):
        primero = procesar_mensaje_productor("chat-corr", "todo junto")
    assert primero.completo is True

    # La conversación se limpió al completarse; se simula que sigue escribiendo.
    with _mock_llm(**_OFERTA_SIN_TELEFONO, telefono_contacto="99"):
        segundo = procesar_mensaje_productor("chat-corr", "ojo, mi número es 99")

    assert segundo.completo is False
    assert segundo.telefono_contacto is None
    assert "parece muy corto" in segundo.pregunta_faltante


def test_nombre_que_no_es_nombre_se_rechaza():
    datos = {**_OFERTA_SIN_TELEFONO, "telefono_contacto": "3001234567", "nombre_productor": "12345"}
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-nom", "irrelevante")

    assert oferta.completo is False
    assert "no parece un nombre" in oferta.pregunta_faltante


# --------------------------------------------------------------------------
# Solo Casanare
# --------------------------------------------------------------------------

_OFERTA_SIN_UBICACION = {
    "producto": "plátano", "cantidad": 20, "unidad": "kg", "precio": 2000,
    "nombre_productor": "Juan Pérez", "telefono_contacto": "3001234567",
}


@pytest.mark.parametrize(
    "ubicacion",
    ["Yopal", "aguazul", "Paz de Ariporo", "Vereda El Charte, Yopal", "orocue"],
)
def test_acepta_municipios_y_veredas_de_casanare(ubicacion):
    with _mock_llm(**_OFERTA_SIN_UBICACION, ubicacion=ubicacion):
        oferta = procesar_mensaje_productor(f"chat-ok-{ubicacion}", "irrelevante")

    assert oferta.completo is True
    assert oferta.ubicacion == ubicacion


@pytest.mark.parametrize(
    "ubicacion",
    [
        "Medellín",          # otro departamento
        "Bogotá",
        "Villavicencio",     # Meta: vecino, pero no es Casanare
        "Vereda La Niata",   # vereda suelta: no se sabe de qué municipio es
    ],
)
def test_rechaza_ubicaciones_que_no_son_de_casanare(ubicacion):
    with _mock_llm(**_OFERTA_SIN_UBICACION, ubicacion=ubicacion):
        oferta = procesar_mensaje_productor(f"chat-no-{ubicacion}", "irrelevante")

    assert oferta.completo is False
    assert oferta.ubicacion is None  # no se guardó
    assert "no reconocí un municipio de Casanare" in oferta.pregunta_faltante
    assert ubicacion in oferta.pregunta_faltante


# --------------------------------------------------------------------------
# Dirección del local (opcional)
# --------------------------------------------------------------------------

def test_ofrece_la_direccion_cuando_falta_poco():
    """Con 1-2 campos obligatorios pendientes se invita a dar la dirección."""
    with _mock_llm(**_OFERTA_SIN_TELEFONO):
        oferta = procesar_mensaje_productor("chat-dir-1", "irrelevante")

    assert oferta.completo is False
    assert "si tienes un local o finca" in oferta.pregunta_faltante.lower()


def test_no_ofrece_la_direccion_cuando_falta_casi_todo():
    """Si faltan muchos campos, la pregunta ya es larga: no se alarga más."""
    with _mock_llm(producto="plátano"):
        oferta = procesar_mensaje_productor("chat-dir-2", "tengo plátano")

    assert "local o finca" not in oferta.pregunta_faltante.lower()


def test_direccion_no_es_obligatoria_para_publicar():
    datos = {**_OFERTA_SIN_TELEFONO, "telefono_contacto": "3001234567"}
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-dir-3", "irrelevante")

    assert oferta.completo is True
    assert oferta.direccion_local is None


def test_direccion_se_guarda_si_la_dan():
    datos = {
        **_OFERTA_SIN_TELEFONO,
        "telefono_contacto": "3001234567",
        "direccion_local": "Calle 20 #5-30, plaza de mercado",
    }
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-dir-4", "irrelevante")

    assert oferta.completo is True
    assert oferta.direccion_local == "Calle 20 #5-30, plaza de mercado"


def test_no_reofrece_la_direccion_si_ya_la_dio():
    """Ya dio la dirección pero le falta el teléfono: no se le vuelve a ofrecer."""
    datos = {**_OFERTA_SIN_TELEFONO, "direccion_local": "Finca La Esperanza"}
    with _mock_llm(**datos):
        oferta = procesar_mensaje_productor("chat-dir-5", "irrelevante")

    assert oferta.completo is False
    assert "local o finca" not in oferta.pregunta_faltante.lower()
