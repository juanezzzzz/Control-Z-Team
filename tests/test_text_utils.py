"""Pruebas de agroia/core/text_utils.py."""
import pytest

from agroia.core.text_utils import normalizar


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
