"""Prueba de humo: la app arranca y el endpoint raíz responde.

Requiere variables de entorno mínimas (ver conftest.py) porque los
routers importan clientes (Anthropic, Groq, Supabase) que necesitan una
API key con la forma correcta, aunque no se llame a ningún servicio real.
"""
from fastapi.testclient import TestClient

from agroia.main import app

client = TestClient(app)

# raise_server_exceptions=False: con credenciales de Supabase falsas, la
# llamada de red puede fallar (DNS, proxy, auth) — nos interesa confirmar
# que la ruta existe y el router responde, no forzar una llamada real.
client_tolerante = TestClient(app, raise_server_exceptions=False)


def test_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_catalogo_route_registrada():
    resp = client_tolerante.get("/api/productos/catalogo")
    assert resp.status_code != 404


def test_publicar_oferta_route_registrada():
    resp = client_tolerante.post("/api/productos", json={"producto": "plátano", "ubicacion": "Yopal"})
    assert resp.status_code != 404


def test_publicar_oferta_valida_campos_obligatorios():
    resp = client_tolerante.post("/api/productos", json={"producto": "  ", "ubicacion": "  "})
    assert resp.status_code == 400


def test_consulta_agente3_route_registrada():
    resp = client_tolerante.post("/api/sistema/agentes/consulta", json={"mensaje": "busco leche"})
    assert resp.status_code != 404
