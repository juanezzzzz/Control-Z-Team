"""Pruebas de la respuesta hablada del bot.

Regla que se verifica: quien manda una nota de voz recibe texto + audio;
quien escribe recibe solo texto. El sintetizador y Telegram se mockean —
acá se prueba la DECISIÓN de hablar, no la síntesis (esa vive en
tests/test_voz.py).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from agroia.agents import agente1_recepcion as agente1
from agroia.agents.clasificador_intencion import COMPRA, VENTA
from agroia.api.routers import webhook as webhook_mod
from agroia.main import app

client = TestClient(app, raise_server_exceptions=False)

AUDIO_FALSO = b"\xff\xf3mp3-de-prueba"


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


def test_si_escribe_no_recibe_audio():
    """A quien escribió, una nota de voz de vuelta le estorba."""
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])

    with patch.object(webhook_mod, "clasificar_intencion", return_value=COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out), \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar_texto, \
         patch.object(webhook_mod, "send_voice", new=AsyncMock()) as enviar_voz, \
         patch.object(webhook_mod, "sintetizar_con_limite", new=AsyncMock()) as sintetiza:
        resp = client.post("/api/webhook/telegram", json=_update_texto("Busco plátano"))

    assert resp.status_code == 200
    enviar_texto.assert_awaited_once()
    enviar_voz.assert_not_awaited()
    sintetiza.assert_not_awaited()  # ni siquiera se gasta en sintetizar


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
