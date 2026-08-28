"""Pruebas del Agente 2: validación, estandarización de unidades y armado
del JSON final.

No tocan la base de datos: `validar_oferta` y `construir_documento` son
funciones puras, y la inserción (`estructurar_y_guardar`) es la única que
habla con Supabase.
"""
import pytest

from agroia.agents import agente2_estructuracion as agente2
from agroia.agents.agente2_estructuracion import (
    OfertaInvalidaError,
    construir_documento,
    estructurar_y_guardar,
    validar_oferta,
)
from agroia.agents.normalizacion import (
    normalizar_producto,
    normalizar_ubicacion,
    normalizar_unidad,
)
from agroia.repositories.productos_repository import ErrorDuplicado
from agroia.schemas import OfertaExtraida


def _oferta(**kwargs) -> OfertaExtraida:
    base = {
        "producto": "plátano",
        "cantidad": 20,
        "unidad": "kg",
        "precio": 2000,
        "ubicacion": "Yopal",
        "completo": True,
    }
    return OfertaExtraida(**{**base, **kwargs})


# --------------------------------------------------------------------------
# Estandarización de unidades
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "escrito, canonica",
    [
        ("kilos", "kg"), ("Kilo", "kg"), ("KG", "kg"), ("kilogramos", "kg"),
        ("libras", "lb"), ("lb", "lb"),
        ("arrobas", "arroba"), ("@", "arroba"),
        ("toneladas", "tonelada"),
        ("litros", "L"), ("lt", "L"),
        ("galones", "galón"),
        ("unidades", "unidad"), ("und", "unidad"),
        ("docenas", "docena"),
        ("costales", "bulto"),
        ("kg.", "kg"),  # con puntuación pegada
    ],
)
def test_normaliza_sinonimos_de_unidad(escrito, canonica):
    unidad = normalizar_unidad(escrito)
    assert unidad is not None
    assert unidad.canonica == canonica


def test_unidad_desconocida_no_se_inventa():
    assert normalizar_unidad("guacal") is None
    assert normalizar_unidad(None) is None
    assert normalizar_unidad("") is None


def test_convierte_arrobas_a_kilos():
    """5 arrobas a $25.000 c/u = 62,5 kg a $2.000/kg."""
    doc = construir_documento(
        _oferta(cantidad=5, unidad="arrobas", precio=25000),
        telegram_user_id="123",
    )
    assert doc["unidad"] == "arroba"
    assert doc["unidad_original"] == "arrobas"
    assert doc["categoria_unidad"] == "peso"
    assert doc["unidad_base"] == "kg"
    assert doc["cantidad_base"] == 62.5
    assert doc["precio_por_unidad_base"] == 2000.0


def test_unidad_sin_equivalencia_fija_no_genera_derivados():
    """Un bulto no pesa siempre lo mismo: mejor null que una conversión inventada."""
    doc = construir_documento(
        _oferta(cantidad=3, unidad="bultos", precio=90000),
        telegram_user_id="123",
    )
    assert doc["unidad"] == "bulto"
    assert doc["categoria_unidad"] == "peso"
    assert doc["cantidad_base"] is None
    assert doc["precio_por_unidad_base"] is None


def test_unidad_desconocida_se_guarda_tal_cual():
    doc = construir_documento(_oferta(unidad="guacales"), telegram_user_id="123")
    assert doc["unidad"] == "guacales"
    assert doc["unidad_original"] == "guacales"
    assert doc["categoria_unidad"] is None
    assert doc["precio_por_unidad_base"] is None


# --------------------------------------------------------------------------
# Estandarización de producto y ubicación
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "escrito, canonico",
    [
        ("PLATANOS", "plátano"), ("  plátano ", "plátano"),
        ("maices", "maíz"), ("limones", "limón"),
        ("sandias", "patilla"),   # en los Llanos se dice patilla
        ("auyama", "ahuyama"),
        ("ñame", "ñame"), ("names", "ñame"),
        ("piñas", "piña"),
    ],
)
def test_normaliza_nombres_de_producto(escrito, canonico):
    assert normalizar_producto(escrito) == canonico


def test_producto_desconocido_no_se_corrompe():
    assert normalizar_producto("  Sacha Inchi ") == "sacha inchi"


@pytest.mark.parametrize(
    "escrito, presentable, municipio",
    [
        ("yopal", "Yopal", "Yopal"),
        ("PAZ DE ARIPORO", "Paz de Ariporo", "Paz de Ariporo"),
        ("orocue", "Orocué", "Orocué"),          # recupera el acento
        ("san luis de palenque", "San Luis de Palenque", "San Luis de Palenque"),
        ("Vereda El Charte, Yopal", "Vereda El Charte, Yopal", "Yopal"),
        ("vereda la niata", "Vereda La Niata", None),  # no es municipio
    ],
)
def test_normaliza_ubicacion(escrito, presentable, municipio):
    assert normalizar_ubicacion(escrito) == (presentable, municipio)


# --------------------------------------------------------------------------
# Validación (entrada del agente)
# --------------------------------------------------------------------------

def test_oferta_completa_no_tiene_errores():
    assert validar_oferta(_oferta()) == []


@pytest.mark.parametrize(
    "campo, valor",
    [("producto", "  "), ("ubicacion", ""), ("cantidad", None), ("precio", None)],
)
def test_detecta_cada_campo_obligatorio_faltante(campo, valor):
    assert validar_oferta(_oferta(**{campo: valor})) != []


def test_rechaza_cantidad_y_precio_no_positivos():
    assert len(validar_oferta(_oferta(cantidad=0, precio=-100))) == 2


def test_no_inserta_si_la_oferta_es_invalida():
    """La excepción se levanta ANTES de llamar al repositorio, por eso esta
    prueba corre sin credenciales reales de Supabase."""
    with pytest.raises(OfertaInvalidaError) as exc:
        estructurar_y_guardar(_oferta(precio=None), telegram_user_id="123")
    assert exc.value.errores == ["Falta el precio."]


# --------------------------------------------------------------------------
# Documento final (salida del agente)
# --------------------------------------------------------------------------

def test_documento_trae_todas_las_columnas_del_esquema():
    doc = construir_documento(
        _oferta(),
        telegram_user_id="123",
        nombre_productor="  Ana  ",
        telefono_contacto=" 3001234567 ",
        direccion_local="  Calle 20 #5-30  ",
    )
    esperadas = {
        "telegram_user_id", "nombre_productor", "telefono_contacto",
        "producto", "cantidad", "unidad", "unidad_original", "categoria_unidad",
        "precio", "ubicacion", "municipio", "direccion_local", "estado", "raw_json",
        "unidad_base", "cantidad_base", "precio_por_unidad_base",
    }
    assert set(doc) == esperadas
    assert doc["estado"] == "activo"
    assert doc["nombre_productor"] == "Ana"
    assert doc["telefono_contacto"] == "573001234567"  # se le completó el indicativo
    assert doc["direccion_local"] == "Calle 20 #5-30"


def test_direccion_local_vacia_queda_en_null():
    """Nunca se guarda cadena vacía: el frontend decide mostrar la fila de
    dirección con un simple chequeo de nulidad."""
    doc = construir_documento(_oferta(), telegram_user_id="123", direccion_local="   ")
    assert doc["direccion_local"] is None


@pytest.mark.parametrize(
    "escrito, esperado",
    [
        # Ya trae indicativo: se conserva.
        ("+57 300 123 4567", "573001234567"),
        ("573001234567", "573001234567"),
        # Celular colombiano sin indicativo: se completa, porque
        # wa.me/3001234567 no resuelve a un chat pero wa.me/573001234567 sí.
        ("(300) 123-4567", "573001234567"),
        ("3001234567", "573001234567"),
        ("310 555 4433", "573105554433"),
        # Fijo: no se le puede inferir indicativo de ciudad, se deja igual.
        ("6358080", "6358080"),
        ("   ", None),
        (None, None),
    ],
)
def test_normaliza_telefono_para_el_link_de_whatsapp(escrito, esperado):
    """El Agente 3 arma el link como https://wa.me/{telefono_contacto}: solo
    funciona con puros dígitos y con indicativo de país."""
    doc = construir_documento(_oferta(), telegram_user_id="123", telefono_contacto=escrito)
    assert doc["telefono_contacto"] == esperado


def test_conserva_la_salida_cruda_del_agente1_para_auditoria():
    oferta = _oferta(unidad="arrobitas")
    doc = construir_documento(oferta, telegram_user_id="123")
    assert doc["raw_json"] == oferta.model_dump()


# --------------------------------------------------------------------------
# Deduplicación (etapa 3)
# --------------------------------------------------------------------------

@pytest.fixture
def repo_falso(monkeypatch):
    """Reemplaza las funciones del repositorio para probar la lógica de
    persistencia del agente sin una base de datos real."""
    llamadas = {"insert": [], "update": [], "existente": None}

    def falso_buscar(telegram_user_id, producto):
        return llamadas["existente"]

    def falso_insertar(payload):
        llamadas["insert"].append(payload)
        return {"id": "nuevo", **payload}

    def falso_actualizar(producto_id, payload):
        llamadas["update"].append((producto_id, payload))
        return {"id": producto_id, **payload}

    monkeypatch.setattr(agente2, "buscar_oferta_activa", falso_buscar)
    monkeypatch.setattr(agente2, "insertar_producto", falso_insertar)
    monkeypatch.setattr(agente2, "actualizar_producto", falso_actualizar)
    return llamadas


def test_inserta_cuando_el_productor_no_tenia_esa_oferta(repo_falso):
    resultado = estructurar_y_guardar(_oferta(), telegram_user_id="123")
    assert len(repo_falso["insert"]) == 1
    assert repo_falso["update"] == []
    assert resultado.actualizada is False


def test_actualiza_en_vez_de_duplicar_si_reenvia_el_mismo_producto(repo_falso):
    """El campesino corrige el precio de su plátano: debe quedar UNA tarjeta."""
    repo_falso["existente"] = {"id": "oferta-previa", "producto": "plátano"}

    resultado = estructurar_y_guardar(_oferta(precio=2500), telegram_user_id="123")

    assert repo_falso["insert"] == []
    assert len(repo_falso["update"]) == 1
    producto_id, payload = repo_falso["update"][0]
    assert producto_id == "oferta-previa"
    assert payload["precio"] == 2500.0
    assert resultado.registro["id"] == "oferta-previa"
    assert resultado.actualizada is True


def test_el_formulario_web_anonimo_nunca_deduplica(repo_falso):
    """Sin teléfono no hay identidad: dos vecinos distintos no deben pisarse."""
    repo_falso["existente"] = {"id": "otra-persona", "producto": "plátano"}

    estructurar_y_guardar(_oferta(), telegram_user_id=agente2.IDENTIDAD_WEB_ANONIMA)

    assert len(repo_falso["insert"]) == 1
    assert repo_falso["update"] == []


def test_rechaza_valores_absurdos_antes_de_tocar_la_base(repo_falso):
    """Una transcripción de voz mala ('dos mil' -> 2000000000) no se publica."""
    with pytest.raises(OfertaInvalidaError):
        estructurar_y_guardar(_oferta(precio=2_000_000_000), telegram_user_id="123")
    assert repo_falso["insert"] == []


def test_carrera_entre_dos_mensajes_termina_en_una_sola_oferta(monkeypatch):
    """Dos mensajes casi simultáneos del mismo campesino: la revisión previa
    no ve nada, pero el índice único de la BD rechaza el segundo insert. El
    agente debe resolverlo como una actualización, no propagar el error."""
    estado = {"consultas": 0, "update": []}

    def falso_buscar(telegram_user_id, producto):
        # La primera consulta (antes del insert) no encuentra nada; la segunda
        # —ya con la fila del otro mensaje escrita— sí.
        estado["consultas"] += 1
        return None if estado["consultas"] == 1 else {"id": "la-que-gano"}

    def falso_insertar(payload):
        raise ErrorDuplicado("duplicate key value violates unique constraint")

    def falso_actualizar(producto_id, payload):
        estado["update"].append(producto_id)
        return {"id": producto_id, **payload}

    monkeypatch.setattr(agente2, "buscar_oferta_activa", falso_buscar)
    monkeypatch.setattr(agente2, "insertar_producto", falso_insertar)
    monkeypatch.setattr(agente2, "actualizar_producto", falso_actualizar)

    resultado = estructurar_y_guardar(_oferta(), telegram_user_id="123")

    assert estado["update"] == ["la-que-gano"]
    assert resultado.actualizada is True
