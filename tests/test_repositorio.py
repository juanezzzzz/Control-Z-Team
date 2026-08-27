"""Pruebas de la traducción de fallos de Supabase a `ErrorPersistencia`.

El caso importante es el silencioso: cuando Row Level Security bloquea una
escritura, Supabase responde 200 con `data` vacío en vez de lanzar un error.
"""
import pytest

from agroia.repositories import productos_repository as repo


class _RespuestaFalsa:
    def __init__(self, data):
        self.data = data


def test_insert_bloqueado_por_rls_da_un_error_explicativo(monkeypatch):
    """Sin la guarda, `data[0]` lanzaría un IndexError que no dice nada."""
    monkeypatch.setattr(
        repo, "_tabla",
        lambda: _TablaFalsa(_RespuestaFalsa([])),
    )
    with pytest.raises(repo.ErrorPersistencia, match="service_role"):
        repo.insertar_producto({"producto": "plátano"})


def test_insert_exitoso_devuelve_la_fila(monkeypatch):
    fila = {"id": "abc", "producto": "plátano"}
    monkeypatch.setattr(repo, "_tabla", lambda: _TablaFalsa(_RespuestaFalsa([fila])))
    assert repo.insertar_producto({"producto": "plátano"}) == fila


def test_error_de_red_se_traduce_a_error_persistencia(monkeypatch):
    def explota():
        raise ConnectionError("DNS falló")

    monkeypatch.setattr(repo, "_tabla", explota)
    with pytest.raises(repo.ErrorPersistencia):
        repo.insertar_producto({"producto": "plátano"})


def test_buscar_oferta_activa_devuelve_none_si_la_consulta_falla(monkeypatch):
    """No poder revisar duplicados no debe impedir publicar una oferta."""
    def explota():
        raise ConnectionError("timeout")

    monkeypatch.setattr(repo, "_tabla", explota)
    assert repo.buscar_oferta_activa("123", "plátano") is None


def test_get_client_avisa_si_faltan_credenciales(monkeypatch):
    monkeypatch.setattr(repo.settings, "SUPABASE_URL", "")
    repo.get_client.cache_clear()
    with pytest.raises(repo.ErrorPersistencia, match="SUPABASE_URL"):
        repo.get_client()
    repo.get_client.cache_clear()


class _TablaFalsa:
    """Imita el encadenamiento de postgrest: .insert().execute()."""

    def __init__(self, respuesta):
        self._respuesta = respuesta

    def insert(self, _payload):
        return self

    def update(self, _payload):
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return self._respuesta
