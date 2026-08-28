"""Pruebas de la respuesta hablada del bot.

Regla que se verifica: el bot responde SIEMPRE con texto + nota de voz, sin
importar si la persona escribió o habló. El sintetizador y Telegram se
mockean — acá se prueba la DECISIÓN de hablar, no la síntesis (esa vive en
tests/test_voz.py).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agroia.agents import agente1_recepcion as agente1
from agroia.agents.clasificador_intencion import COMPRA, VENTA
from agroia.api.routers import webhook as webhook_mod
from agroia.main import app

client = TestClient(app, raise_server_exceptions=False)

AUDIO_FALSO = b"\xff\xf3mp3-de-prueba"


@pytest.fixture(autouse=True)
def voz_encendida():
    """conftest.py apaga la voz para toda la suite (si no, cada prueba saldría
    a sintetizar por red). Este archivo es el que la prueba, así que la
    enciende — el sintetizador siempre va mockeado."""
    with patch.object(webhook_mod.settings, "VOZ_RESPUESTA_ACTIVA", True):
        yield


def _update_texto(texto: str) -> dict:
    return {"message": {"chat": {"id": 123}, "text": texto}}


def _update_voz() -> dict:
    return {"message": {"chat": {"id": 123}, "voice": {"file_id": "AwACAgEAAx"}}}


def setup_function():
    agente1.CONVERSACIONES.clear()


def teardown_function():
    agente1.CONVERSACIONES.clear()


def _mocks_de_voz(audio=AUDIO_FALSO):
    """Mockea la cadena de voz completa: descarga, transcripción y síntesis."""
    return (
        patch.object(webhook_mod, "get_file_path", new=AsyncMock(return_value="voice/f.oga")),
        patch.object(webhook_mod, "download_file", new=AsyncMock(return_value=b"ogg")),
        patch.object(webhook_mod, "transcribir_audio", return_value="Busco plátano por Yopal"),
        patch.object(webhook_mod, "sintetizar_con_limite", new=AsyncMock(return_value=audio)),
    )


def test_si_manda_nota_de_voz_recibe_texto_y_audio():
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    ruta, descarga, transcribe, sintetiza = _mocks_de_voz()

    with ruta, descarga, transcribe, sintetiza, \
         patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz:
        resp = client.post("/api/webhook/telegram", json=_update_voz())

    assert resp.status_code == 200
    enviar_texto.assert_awaited_once()          # el texto SIEMPRE se manda
    enviar_voz.assert_awaited_once()            # y además el audio
    assert enviar_voz.await_args.args[1] == AUDIO_FALSO


def test_si_escribe_tambien_recibe_audio():
    """Quien lee con dificultad igual puede escribir como pueda: condicionar
    el audio al canal de entrada dejaría por fuera a quien más lo necesita."""
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])

    with patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz, \
         patch.object(webhook_mod, "sintetizar_con_limite",
                      new=AsyncMock(return_value=AUDIO_FALSO)):
        resp = client.post("/api/webhook/telegram", json=_update_texto("Busco plátano"))

    assert resp.status_code == 200
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_awaited_once()


def test_el_texto_va_primero_y_siempre():
    """Orden: primero el mensaje escrito (del que se copia un teléfono),
    después el audio. Si se invirtiera, una síntesis lenta retrasaría la
    respuesta útil."""
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    orden: list[str] = []

    async def registrar_texto(*_a, **_k):
        orden.append("texto")

    async def registrar_voz(*_a, **_k):
        orden.append("voz")

    with patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=registrar_texto), \
         patch.object(webhook_mod, "send_voice", new=registrar_voz), \
         patch.object(webhook_mod, "sintetizar_con_limite",
                      new=AsyncMock(return_value=AUDIO_FALSO)):
        client.post("/api/webhook/telegram", json=_update_texto("Busco plátano"))

    assert orden == ["texto", "voz"]


def test_el_aviso_de_adjunto_no_soportado_tambien_se_habla():
    """Una foto sin descripción la manda seguido quien no escribe bien: es
    justo a quien hay que contestarle hablado."""
    with patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz, \
         patch.object(webhook_mod, "sintetizar_con_limite",
                      new=AsyncMock(return_value=AUDIO_FALSO)):
        resp = client.post(
            "/api/webhook/telegram",
            json={"message": {"chat": {"id": 123}, "photo": [{"file_id": "x"}]}},
        )

    assert resp.json()["flujo"] == "no_soportado"
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_awaited_once()


def test_si_la_sintesis_falla_igual_llega_el_texto():
    """El audio es un extra: que falle no puede dejar al productor sin respuesta."""
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    ruta, descarga, transcribe, sintetiza = _mocks_de_voz(audio=None)

    with ruta, descarga, transcribe, sintetiza, \
         patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz:
        resp = client.post("/api/webhook/telegram", json=_update_voz())

    assert resp.status_code == 200
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_not_awaited()


def test_la_pregunta_del_agente1_tambien_se_habla():
    """El ida y vuelta de 'faltan datos' es donde más importa la voz: es
    cuando el productor está respondiendo preguntas una por una."""
    oferta_incompleta = SimpleNamespace(completo=False, pregunta_faltante="¿A qué precio lo vende?")
    ruta, descarga, transcribe, sintetiza = _mocks_de_voz()

    with ruta, descarga, transcribe, sintetiza, \
         patch.object(webhook_mod, "clasificar_intencion", return_value=VENTA), \
         patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_incompleta), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz:
        resp = client.post("/api/webhook/telegram", json=_update_voz())

    assert resp.status_code == 200
    assert resp.json()["completo"] is False
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_awaited_once()


def test_se_puede_apagar_la_voz_con_una_variable():
    """VOZ_RESPUESTA_ACTIVA=false deja el bot como estaba, solo texto."""
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    ruta, descarga, transcribe, sintetiza = _mocks_de_voz()

    with ruta, descarga, transcribe, sintetiza, \
         patch.object(webhook_mod.settings, "VOZ_RESPUESTA_ACTIVA", False), \
         patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz:
        resp = client.post("/api/webhook/telegram", json=_update_voz())

    assert resp.status_code == 200
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_not_awaited()
