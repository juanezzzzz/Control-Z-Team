"""Pruebas de la heurística de enrutamiento del webhook de Telegram
(`_es_intencion_compra`) y del webhook completo con los agentes mockeados.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from agroia.api.routers import webhook as webhook_mod
from agroia.api.routers.webhook import _es_intencion_compra
from agroia.main import app

client = TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    "mensaje",
    [
        "Busco plátano por Yopal",
        "necesito leche cerca de Aguazul",
        "Estoy buscando yuca",
        "¿Alguien vende queso?",
        "quiero comprar maíz",
        "hay tomate por Tauramena?",
    ],
)
def test_detecta_compra(mensaje):
    assert _es_intencion_compra(mensaje) is True


@pytest.mark.parametrize(
    "mensaje",
    [
        "Vendo 20 kilos de plátano a 2000 pesos",
        "Tengo leche disponible en Yopal",
        "Ofrezco yuca fresca",
        "quiero vender mi cosecha de café",
        "50 arrobas de arroz",
    ],
)
def test_detecta_venta_u_otro(mensaje):
    assert _es_intencion_compra(mensaje) is False


def _update(texto: str) -> dict:
    return {"message": {"chat": {"id": 123}, "text": texto}}


def test_webhook_enruta_compra_al_agente3():
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    with patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out) as ag3, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar:
        resp = client.post("/api/webhook/telegram", json=_update("Busco plátano por Yopal"))

    assert resp.status_code == 200
    assert resp.json()["flujo"] == "compra"
    ag3.assert_called_once_with("Busco plátano por Yopal")
    enviar.assert_awaited_once()


def test_webhook_enruta_oferta_al_agente1():
    oferta_incompleta = SimpleNamespace(completo=False, pregunta_faltante="¿A qué precio?")
    with patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_incompleta) as ag1, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar:
        resp = client.post("/api/webhook/telegram", json=_update("Vendo 20 kilos de plátano"))

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "flujo": "productor", "completo": False}
    ag1.assert_called_once()
    enviar.assert_awaited_once_with(123, "¿A qué precio?")


def test_webhook_pasa_nombre_y_telefono_al_agente2():
    """Antes de esto, el flujo de Telegram nunca guardaba nombre ni teléfono
    del productor: estructurar_y_guardar se llamaba sin esos kwargs."""
    oferta_completa = SimpleNamespace(
        completo=True,
        pregunta_faltante=None,
        producto="plátano",
        nombre_productor="Juan Pérez",
        telefono_contacto="3001234567",
    )
    resultado_falso = SimpleNamespace(
        registro={"id": "abc123", "producto": "plátano"},
        actualizada=False,
    )
    with patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_completa), \
         patch.object(webhook_mod, "estructurar_y_guardar", return_value=resultado_falso) as ag2, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()):
        resp = client.post("/api/webhook/telegram", json=_update("Vendo plátano, soy Juan, mi cel es 3001234567"))

    assert resp.status_code == 200
    assert resp.json()["completo"] is True
    _, kwargs = ag2.call_args
    assert kwargs["nombre_productor"] == "Juan Pérez"
    assert kwargs["telefono_contacto"] == "3001234567"


def test_webhook_ignora_update_sin_mensaje():
    resp = client.post("/api/webhook/telegram", json={"edited_message": {"foo": "bar"}})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_webhook_ignora_texto_vacio():
    resp = client.post("/api/webhook/telegram", json=_update("   "))
    assert resp.status_code == 200
    assert resp.json()["flujo"] == "ninguno"
