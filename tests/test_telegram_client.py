"""Pruebas de `parse_update`: cómo se normaliza cada update de Telegram."""
import pytest

from agroia.integrations.telegram_client import parse_update


def _msg(**contenido) -> dict:
    return {"message": {"chat": {"id": 123}, **contenido}}


def test_texto():
    assert parse_update(_msg(text="Vendo papa")) == {
        "chat_id": 123, "tipo": "texto", "texto": "Vendo papa",
    }


def test_nota_de_voz():
    parsed = parse_update(_msg(voice={"file_id": "abc123"}))
    assert parsed == {"chat_id": 123, "tipo": "audio", "voice_file_id": "abc123"}


@pytest.mark.parametrize(
    "contenido, nombre",
    [
        ({"photo": [{"file_id": "f1"}]}, "una foto"),
        ({"video": {"file_id": "v1"}}, "un video"),
        ({"video_note": {"file_id": "vn1"}}, "un video"),
        ({"sticker": {"file_id": "s1"}}, "un sticker"),
        ({"document": {"file_id": "d1"}}, "un archivo"),
        ({"audio": {"file_id": "a1"}}, "un archivo de audio"),
        ({"location": {"latitude": 5.3, "longitude": -72.4}}, "una ubicación"),
        ({"contact": {"phone_number": "300"}}, "un contacto"),
    ],
)
def test_adjuntos_no_soportados_se_reportan_para_poder_responder(contenido, nombre):
    """Lo importante: NO devolver None. Con None el bot se quedaba mudo y la
    persona no sabía si su mensaje había llegado."""
    parsed = parse_update(_msg(**contenido))
    assert parsed == {"chat_id": 123, "tipo": "no_soportado", "adjunto": nombre}


def test_gif_se_nombra_como_gif_y_no_como_archivo():
    """Telegram manda un GIF con `animation` Y `document` a la vez."""
    parsed = parse_update(_msg(animation={"file_id": "g1"}, document={"file_id": "g1"}))
    assert parsed["adjunto"] == "un GIF"


def test_foto_con_descripcion_usa_la_descripcion():
    """Mandar la foto de la cosecha con 'vendo 20 kg de papa' es lo natural:
    esa descripción es el mensaje de verdad y debe procesarse como texto."""
    parsed = parse_update(_msg(photo=[{"file_id": "f1"}], caption="Vendo 20 kg de papa"))
    assert parsed == {"chat_id": 123, "tipo": "texto", "texto": "Vendo 20 kg de papa"}


def test_descripcion_vacia_no_cuenta_como_texto():
    parsed = parse_update(_msg(photo=[{"file_id": "f1"}], caption="   "))
    assert parsed["tipo"] == "no_soportado"


@pytest.mark.parametrize(
    "update",
    [
        {},                                        # update vacío
        {"edited_message": {"text": "algo"}},      # edición: no es mensaje nuevo
        {"my_chat_member": {"chat": {"id": 1}}},   # bot añadido a un grupo
    ],
)
def test_updates_sin_mensaje_de_una_persona_devuelven_none(update):
    """Acá sí corresponde None: no hay a quién responderle."""
    assert parse_update(update) is None


def test_mensaje_sin_contenido_reconocible_devuelve_none():
    """Un service message (ej. 'fulano entró al grupo') no trae adjunto."""
    assert parse_update(_msg(new_chat_members=[])) is None
