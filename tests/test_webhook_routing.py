"""Pruebas del enrutamiento del webhook de Telegram.

El clasificador de intención (`clasificar_intencion`) se mockea: acá se
prueba el ENRUTAMIENTO, no la clasificación en sí (esa vive en
tests/test_clasificador_intencion.py).
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from agroia.agents import agente1_recepcion as agente1
from agroia.agents.clasificador_intencion import COMPRA, DESCONOCIDA, VENTA
from agroia.api.routers import webhook as webhook_mod
from agroia.main import app

client = TestClient(app, raise_server_exceptions=False)


def _update(texto: str) -> dict:
    return {"message": {"chat": {"id": 123}, "text": texto}}


def _con_intencion(intencion: str):
    return patch.object(webhook_mod, "clasificar_intencion", return_value=intencion)


def setup_function():
    """Cada prueba arranca sin conversaciones a medias."""
    agente1.CONVERSACIONES.clear()


def teardown_function():
    agente1.CONVERSACIONES.clear()


def test_intencion_de_compra_va_al_agente3():
    fake_out = SimpleNamespace(respuesta_texto="Encontré 1 oferta(s):", resultados=[{}])
    with _con_intencion(COMPRA), \
         patch.object(webhook_mod, "atender_consulta_comprador", return_value=fake_out) as ag3, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar:
        resp = client.post("/api/webhook/telegram", json=_update("Busco plátano por Yopal"))

    assert resp.status_code == 200
    assert resp.json()["flujo"] == "compra"
    ag3.assert_called_once_with("Busco plátano por Yopal")
    enviar.assert_awaited_once()


def test_intencion_de_venta_va_al_agente1():
    oferta_incompleta = SimpleNamespace(completo=False, pregunta_faltante="¿A qué precio?")
    with _con_intencion(VENTA), \
         patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_incompleta) as ag1, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar:
        resp = client.post("/api/webhook/telegram", json=_update("Vendo 20 kilos de plátano"))

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "flujo": "productor", "completo": False}
    ag1.assert_called_once()
    enviar.assert_awaited_once_with(123, "¿A qué precio?")


def test_intencion_desconocida_pregunta_que_quiere_hacer():
    """Un "hola" no debe arrancar el flujo de venta: el bot ofrece el menú."""
    with _con_intencion(DESCONOCIDA), \
         patch.object(webhook_mod, "procesar_mensaje_productor") as ag1, \
         patch.object(webhook_mod, "atender_consulta_comprador") as ag3, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()) as enviar:
        resp = client.post("/api/webhook/telegram", json=_update("hola"))

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "flujo": "desconocida"}
    ag1.assert_not_called()
    ag3.assert_not_called()

    (_, mensaje), _ = enviar.await_args
    assert "VENDER" in mensaje and "COMPRAR" in mensaje


def test_conversacion_en_curso_no_se_reclasifica():
    """Si el productor está a mitad de publicar, su "Yopal" es la respuesta a
    una pregunta — no un mensaje suelto que haya que volver a clasificar."""
    agente1.CONVERSACIONES["123"] = {"producto": "papa"}
    oferta_incompleta = SimpleNamespace(completo=False, pregunta_faltante="¿A qué precio?")

    with patch.object(webhook_mod, "clasificar_intencion") as clasificador, \
         patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_incompleta) as ag1, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()):
        resp = client.post("/api/webhook/telegram", json=_update("Yopal"))

    assert resp.status_code == 200
    clasificador.assert_not_called()
    ag1.assert_called_once()


def test_webhook_pasa_nombre_telefono_y_direccion_al_agente2():
    """Antes de esto, el flujo de Telegram nunca guardaba nombre ni teléfono
    del productor: estructurar_y_guardar se llamaba sin esos kwargs."""
    oferta_completa = SimpleNamespace(
        completo=True,
        pregunta_faltante=None,
        producto="plátano",
        nombre_productor="Juan Pérez",
        telefono_contacto="3001234567",
        direccion_local="Calle 20 #5-30",
    )
    resultado_falso = SimpleNamespace(
        registro={"id": "abc123", "producto": "plátano"},
        actualizada=False,
    )
    with _con_intencion(VENTA), \
         patch.object(webhook_mod, "procesar_mensaje_productor", return_value=oferta_completa), \
         patch.object(webhook_mod, "estructurar_y_guardar", return_value=resultado_falso) as ag2, \
         patch.object(webhook_mod, "send_message", new=AsyncMock()):
        resp = client.post("/api/webhook/telegram", json=_update("Vendo plátano, soy Juan, cel 3001234567"))

    assert resp.status_code == 200
    assert resp.json()["completo"] is True
    _, kwargs = ag2.call_args
    assert kwargs["nombre_productor"] == "Juan Pérez"
    assert kwargs["telefono_contacto"] == "3001234567"
    assert kwargs["direccion_local"] == "Calle 20 #5-30"


def test_webhook_ignora_update_sin_mensaje():
    resp = client.post("/api/webhook/telegram", json={"edited_message": {"foo": "bar"}})
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_webhook_ignora_texto_vacio():
    resp = client.post("/api/webhook/telegram", json=_update("   "))
    assert resp.status_code == 200
    assert resp.json()["flujo"] == "ninguno"
