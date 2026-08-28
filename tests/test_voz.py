"""Pruebas de la adaptación de texto a voz y del tono llanero.

Son funciones puras: no llaman al sintetizador ni a la red.
"""
import pytest

from agroia.core.voz import (
    dar_fluidez,
    dar_tono_llanero,
    preparar_para_voz,
    texto_hablado,
    unir_campos,
)


# --------------------------------------------------------------------------
# Números, moneda y unidades
# --------------------------------------------------------------------------

def test_precio_se_dice_en_pesos_no_en_dolares():
    """'$' lo pronunciaría como 'dólares'; acá son pesos colombianos. Y el
    precio por unidad se dice 'el kilo', no 'por kilos' (ver dar_fluidez)."""
    assert preparar_para_voz("Quedó a $2.000 por kg") == "Quedó a 2000 pesos el kilo"


def test_separador_de_miles_se_quita():
    """'2.000' con punto se puede leer como decimal; '2000' se lee 'dos mil'."""
    assert "25000" in preparar_para_voz("Son 25.000 la arroba")
    assert "1500000" in preparar_para_voz("Vale 1.500.000")


def test_no_rompe_un_decimal_con_coma():
    """En formato colombiano el decimal va con coma: no debe tocarse."""
    assert "62,5" in preparar_para_voz("Son 62,5 kilos")


@pytest.mark.parametrize(
    "escrito, hablado",
    [
        ("20 kg", "20 kilos"),
        ("500 g", "500 gramos"),
        ("3 lb", "3 libras"),
        ("2 L", "2 litros"),
        ("250 ml", "250 mililitros"),
        ("12 und", "12 unidades"),
        ("5 @", "5 arrobas"),
    ],
)
def test_abreviaturas_de_unidad_se_dicen_completas(escrito, hablado):
    assert preparar_para_voz(escrito) == hablado


def test_celular_se_dicta_digito_por_digito():
    """Un celular dicho como número entero es imposible de anotar."""
    resultado = preparar_para_voz("Llame al 3001234567")
    assert "3 0 0 1 2 3 4 5 6 7" in resultado


# --------------------------------------------------------------------------
# Ruido que no se puede pronunciar
# --------------------------------------------------------------------------

def test_enlaces_se_eliminan():
    """Un wa.me dicho en voz alta es ruido; el dato va en el mensaje escrito."""
    resultado = preparar_para_voz("Contacto: wa.me/573001234567 para hablar")
    assert "wa.me" not in resultado
    assert "573001234567" not in resultado
    assert "para hablar" in resultado


def test_etiqueta_sin_contenido_se_elimina():
    """Al quitar el enlace, 'Contacto:' quedaría dicho como frase a medias."""
    resultado = preparar_para_voz("Precio 2000. Contacto: wa.me/573001234567")
    assert "Contacto" not in resultado
    assert "2000" in resultado


def test_no_se_come_una_etiqueta_que_si_tiene_contenido():
    """Regresión: 'Encontré 2 ofertas:' perdía la palabra 'ofertas' porque la
    limpieza de etiquetas huérfanas borraba cualquier palabra con dos puntos
    seguida de una pausa. Solo debe borrarse la que introducía un enlace."""
    resultado = preparar_para_voz("Encontré 2 oferta(s):\n\n• Plátano - 20 kg")
    assert "ofertas" in resultado
    assert "Plátano" in resultado


def test_emojis_y_vinetas_se_eliminan():
    resultado = preparar_para_voz("🌾 Oferta nueva\n• plátano\n• yuca")
    assert "🌾" not in resultado
    assert "•" not in resultado
    assert "plátano" in resultado and "yuca" in resultado


def test_saltos_de_linea_se_vuelven_pausas():
    resultado = preparar_para_voz("Primera línea\n\nSegunda línea")
    assert "\n" not in resultado
    assert "Primera línea. Segunda línea" == resultado


def test_no_deja_espacios_ni_puntos_duplicados():
    resultado = preparar_para_voz("Hola   mundo .. bien")
    assert "  " not in resultado
    assert ".." not in resultado


# --------------------------------------------------------------------------
# Fluidez: que no suene a texto leído por una máquina
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "escrito, hablado",
    [
        ("2000 pesos por kilos", "2000 pesos el kilo"),
        ("500 pesos por libras", "500 pesos la libra"),
        ("3000 pesos por litros", "3000 pesos el litro"),
        ("800 pesos por unidades", "800 pesos la unidad"),
        ("25000 pesos por arrobas", "25000 pesos la arroba"),
    ],
)
def test_el_precio_por_unidad_se_dice_como_habla_la_gente(escrito, hablado):
    """Nadie dice 'a 2000 pesos por kilos'; se dice 'el kilo'. La expansión
    de unidades pluraliza siempre, y eso delata a la máquina."""
    assert dar_fluidez(escrito) == hablado


def test_la_cantidad_si_va_en_plural():
    """Cuidado: el arreglo del precio no debe tocar '20 kilos'."""
    assert "20 kilos" in dar_fluidez("Tengo 20 kilos a 2000 pesos por kilos")


def test_los_campos_se_unen_con_preposiciones_no_con_comas():
    """Cada coma es una pausa: cuatro comas seguidas salen a tirones. Con
    preposiciones la oferta se dice de corrido."""
    unido = unir_campos("Plátano - 20 kg - $2.000 - Yopal")
    assert unido == "Plátano de 20 kg a $2.000 en Yopal"
    assert "," not in unido


def test_la_oferta_hablada_no_queda_llena_de_pausas():
    hablado = preparar_para_voz("• Plátano - 20 kg - $2.000 - Yopal")
    assert "de 20 kilos" in hablado
    assert "a 2000 pesos" in hablado
    assert "en Yopal" in hablado
    # Solo la coma del ordinal; ninguna entre los campos.
    assert hablado.count(",") == 1


def test_las_ofertas_se_enumeran_en_vez_de_leerse_de_corrido():
    """Enumerar es lo que haría alguien contando las ofertas por teléfono.
    Con coma, no con dos puntos: la pausa es breve y no corta la frase."""
    escrito = "Encontré 2 ofertas:\n• Plátano - 20 kg\n• Yuca - 5 @"
    hablado = preparar_para_voz(escrito)

    assert "La primera," in hablado
    assert "La segunda," in hablado
    assert "•" not in hablado


def test_una_sola_oferta_tambien_se_enumera_sin_romperse():
    hablado = preparar_para_voz("Encontré 1 oferta:\n• Plátano - 20 kg")
    assert "La primera," in hablado
    assert "La segunda," not in hablado


def test_mas_ofertas_que_ordinales_no_revienta():
    """El Agente 3 devuelve máximo 5, pero el código no debe asumirlo."""
    vinetas = "".join(f"\n• Producto{i} - 1 kg" for i in range(8))
    hablado = preparar_para_voz(f"Encontré 8 ofertas:{vinetas}")
    assert "La quinta," in hablado
    assert "Y otra," in hablado


# --------------------------------------------------------------------------
# Tono llanero
# --------------------------------------------------------------------------

def test_saludo_llanero():
    assert dar_tono_llanero("¡Hola! Soy AgroIA").startswith("¡Buenas!")
    assert dar_tono_llanero("Hola, vecino") == "Buenas, vecino"


def test_usa_hallar_en_vez_de_encontrar():
    """En el Llano se dice 'hallar' mucho más que 'encontrar'."""
    assert "No le hallé" in dar_tono_llanero("No encontré ofertas activas")


def test_confirmacion_calida():
    assert "¡Listo pues!" in dar_tono_llanero("¡Listo! Publiqué tu oferta")


def test_el_tono_no_altera_los_datos():
    """El tono cambia palabras de cortesía, nunca cifras ni nombres propios."""
    original = "¡Listo! Publiqué tu oferta de plátano. Quedó a $2.000 por kg en Yopal."
    con_tono = dar_tono_llanero(original)
    for dato in ("plátano", "$2.000", "kg", "Yopal"):
        assert dato in con_tono


# --------------------------------------------------------------------------
# Pipeline completo
# --------------------------------------------------------------------------

def test_confirmacion_real_del_bot_queda_hablable():
    """El mensaje que hoy manda el webhook tras publicar una oferta."""
    escrito = (
        "¡Listo! Publiqué tu oferta de plátano en el catálogo. "
        "Quedó a $2.000 por kg. Los compradores ya pueden verla y contactarte."
    )
    hablado = texto_hablado(escrito)

    assert "¡Listo pues!" in hablado
    assert "2000 pesos el kilo" in hablado   # no "por kilos"
    assert "vecino" in hablado
    assert "$" not in hablado
    assert " kg" not in hablado


def test_respuesta_del_agente3_queda_hablable():
    """La respuesta de ventas trae enlaces y viñetas: lo peor para una voz."""
    escrito = (
        "Encontré 2 oferta(s):\n\n"
        "• Plátano - 20 kg - $2.000 - Yopal\n  Contacto: wa.me/573001234567"
    )
    hablado = texto_hablado(escrito)

    assert "wa.me" not in hablado
    assert "•" not in hablado
    assert "\n" not in hablado
    assert "2000 pesos" in hablado
    assert "Le hallé" in hablado
    # Los guiones se vuelven preposiciones: la oferta sale como una frase
    # corrida, sin las pausas que dejaban las comas.
    assert "Plátano de 20 kilos a 2000 pesos en Yopal" in hablado
