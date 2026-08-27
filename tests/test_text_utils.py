"""Pruebas de agroia/core/text_utils.py."""
import pytest

from agroia.core.text_utils import extraer_json, normalizar


class TestExtraerJson:
    def test_json_puro(self):
        assert extraer_json('{"producto": "leche", "ubicacion": null}') == {
            "producto": "leche",
            "ubicacion": None,
        }

    def test_json_con_texto_alrededor(self):
        texto = 'Claro, aquí tienes:\n{"producto": "yuca", "ubicacion": "Yopal"}\n¡Listo!'
        assert extraer_json(texto) == {"producto": "yuca", "ubicacion": "Yopal"}

    def test_json_en_bloque_markdown(self):
        texto = '```json\n{"producto": "plátano"}\n```'
        assert extraer_json(texto) == {"producto": "plátano"}

    def test_sin_json_lanza_valueerror(self):
        with pytest.raises(ValueError):
            extraer_json("no encontré nada útil que responder")

    def test_cadena_vacia_lanza_valueerror(self):
        with pytest.raises(ValueError):
            extraer_json("")

    def test_json_no_objeto_lanza_valueerror(self):
        with pytest.raises(ValueError):
            extraer_json("[1, 2, 3]")


class TestNormalizar:
    @pytest.mark.parametrize(
        "entrada,esperado",
        [
            ("Plátano", "platano"),
            ("  YOPAL  ", "yopal"),
            ("Aguazul, Casanare", "aguazul casanare"),
            ("¿Alguien vende queso?", "alguien vende queso"),
            ("queso   campesino", "queso campesino"),
            (None, ""),
            ("", ""),
        ],
    )
    def test_normalizar(self, entrada, esperado):
        assert normalizar(entrada) == esperado
