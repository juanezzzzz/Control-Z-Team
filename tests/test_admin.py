"""Pruebas del panel de administrador: login (agroia/core/admin_auth.py) y
las rutas de moderación (agroia/api/routers/admin.py).

Ningún test llama a Supabase de verdad: las rutas protegidas mockean el
repositorio, igual que test_webhook_routing.py hace con los agentes.
"""
import pytest
from fastapi.testclient import TestClient

from agroia.api.routers import admin as admin_router
from agroia.core import admin_auth
from agroia.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def limpiar_sesiones():
    admin_auth._sesiones.clear()
    admin_auth._intentos_fallidos.clear()
    yield
    admin_auth._sesiones.clear()
    admin_auth._intentos_fallidos.clear()


@pytest.fixture
def admin_configurado(monkeypatch):
    monkeypatch.setattr(admin_auth.settings, "ADMIN_USERNAME", "admin")
    monkeypatch.setattr(admin_auth.settings, "ADMIN_PASSWORD", "clave-segura")


# --- agroia/core/admin_auth.py -------------------------------------------


def test_login_exitoso_devuelve_un_token(admin_configurado):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    assert token and isinstance(token, str)


def test_login_con_clave_incorrecta_rechaza(admin_configurado):
    with pytest.raises(admin_auth.CredencialesInvalidas):
        admin_auth.iniciar_sesion("admin", "clave-equivocada")


def test_login_sin_admin_configurado_rechaza():
    with pytest.raises(admin_auth.CredencialesInvalidas):
        admin_auth.iniciar_sesion("admin", "lo-que-sea")


@pytest.mark.parametrize(
    "usuario, contrasena",
    [
        ("josé", "clave-segura"),        # tilde en el usuario
        ("admin", "contraseñ4"),         # eñe en la contraseña
        ("admin", "clavé-segura"),       # tilde en la contraseña
    ],
)
def test_credenciales_con_tildes_o_enes_no_revientan(admin_configurado, usuario, contrasena):
    """hmac.compare_digest lanza TypeError con caracteres no ASCII si se le
    pasan `str`. Sin comparar en bytes, una clave con ñ —normal en Colombia—
    devolvía un 500 en vez de un 401, y era imposible usarla como contraseña."""
    with pytest.raises(admin_auth.CredencialesInvalidas):
        admin_auth.iniciar_sesion(usuario, contrasena)


def test_una_contrasena_con_ene_si_puede_ser_la_correcta(monkeypatch):
    """No basta con no reventar: la clave con ñ tiene que FUNCIONAR."""
    monkeypatch.setattr(admin_auth.settings, "ADMIN_USERNAME", "josé")
    monkeypatch.setattr(admin_auth.settings, "ADMIN_PASSWORD", "contraseñ4-muy-segura")

    token = admin_auth.iniciar_sesion("josé", "contraseñ4-muy-segura")
    assert token and isinstance(token, str)


def test_login_http_con_tildes_devuelve_401_no_500(admin_configurado):
    resp = client.post("/api/admin/login", json={"usuario": "josé", "contrasena": "x"})
    assert resp.status_code == 401


def test_tras_varios_fallos_bloquea_ese_usuario(admin_configurado):
    for _ in range(admin_auth._MAX_INTENTOS):
        with pytest.raises(admin_auth.CredencialesInvalidas):
            admin_auth.iniciar_sesion("admin", "clave-mala")

    with pytest.raises(admin_auth.DemasiadosIntentos):
        admin_auth.iniciar_sesion("admin", "clave-segura")  # ni con la clave correcta


def test_requiere_admin_acepta_token_de_una_sesion_vigente(admin_configurado):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    admin_auth.requiere_admin(authorization=f"Bearer {token}")  # no debe lanzar


def test_requiere_admin_rechaza_sin_token():
    with pytest.raises(Exception):
        admin_auth.requiere_admin(authorization=None)


def test_requiere_admin_rechaza_token_desconocido():
    with pytest.raises(Exception):
        admin_auth.requiere_admin(authorization="Bearer token-inventado")


# --- agroia/api/routers/admin.py ------------------------------------------


def test_login_route_credenciales_correctas(admin_configurado):
    resp = client.post("/api/admin/login", json={"usuario": "admin", "contrasena": "clave-segura"})
    assert resp.status_code == 200
    assert resp.json()["token"]


def test_login_route_credenciales_incorrectas(admin_configurado):
    resp = client.post("/api/admin/login", json={"usuario": "admin", "contrasena": "mala"})
    assert resp.status_code == 401


def test_listar_productos_sin_token_da_401():
    resp = client.get("/api/admin/productos")
    assert resp.status_code == 401


def test_listar_productos_con_token_valido(admin_configurado, monkeypatch):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    monkeypatch.setattr(
        admin_router,
        "listar_todos",
        lambda: [{"id": "1", "producto": "papa", "estado": "vendido"}],
    )
    resp = client.get("/api/admin/productos", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()[0]["producto"] == "papa"


def test_cambiar_estado_con_valor_invalido_da_400(admin_configurado):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    resp = client.patch(
        "/api/admin/productos/1/estado",
        json={"estado": "no-existe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400


def test_cambiar_estado_valido_actualiza(admin_configurado, monkeypatch):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    monkeypatch.setattr(
        admin_router,
        "actualizar_producto",
        lambda _id, payload: {"id": "1", "producto": "papa", "estado": payload["estado"]},
    )
    resp = client.patch(
        "/api/admin/productos/1/estado",
        json={"estado": "vendido"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["estado"] == "vendido"


def test_eliminar_producto_sin_token_da_401():
    resp = client.delete("/api/admin/productos/1")
    assert resp.status_code == 401


def test_eliminar_producto_con_token_valido(admin_configurado, monkeypatch):
    token = admin_auth.iniciar_sesion("admin", "clave-segura")
    monkeypatch.setattr(admin_router, "eliminar_producto", lambda _id: None)
    resp = client.delete("/api/admin/productos/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 204
