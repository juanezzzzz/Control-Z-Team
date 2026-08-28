"""Autenticación del panel de administrador (/admin en el frontend).

Un solo usuario admin, configurado en ADMIN_USERNAME/ADMIN_PASSWORD — no hay
gestión de usuarios ni roles: alcanza para moderar ofertas en el MVP de
hackathon, no es un sistema multi-usuario.

Las sesiones (token -> vencimiento) y los intentos fallidos viven en memoria,
mismo criterio que CONVERSACIONES en agente1_recepcion.py: si el proceso se
reinicia, el admin tiene que volver a iniciar sesión. Suficiente para el
tamaño de este proyecto; si hiciera falta persistirlas, el cambio queda
contenido en este único módulo.
"""
import hmac
import secrets
import time
from typing import Optional

from fastapi import Header, HTTPException

from agroia.core.config import settings

_TOKEN_TTL_SEGUNDOS = 12 * 60 * 60  # 12 horas
_MAX_INTENTOS = 5
_BLOQUEO_SEGUNDOS = 5 * 60

_sesiones: dict[str, float] = {}  # token -> vence_en (epoch)
_intentos_fallidos: dict[str, list[float]] = {}  # usuario -> timestamps de fallos recientes


class CredencialesInvalidas(Exception):
    """Usuario/contraseña no coinciden, o el panel no está configurado."""


class DemasiadosIntentos(Exception):
    """Ese usuario superó el máximo de intentos fallidos recientes."""


def _bloqueado(usuario: str) -> bool:
    ahora = time.time()
    vigentes = [t for t in _intentos_fallidos.get(usuario, []) if ahora - t < _BLOQUEO_SEGUNDOS]
    _intentos_fallidos[usuario] = vigentes
    return len(vigentes) >= _MAX_INTENTOS


def iniciar_sesion(usuario: str, contrasena: str) -> str:
    """Valida usuario/contraseña contra el admin configurado y devuelve un
    token de sesión nuevo. Lanza CredencialesInvalidas o DemasiadosIntentos —
    nunca revela si el usuario existía, solo si el intento fue válido."""
    if not settings.ADMIN_USERNAME or not settings.ADMIN_PASSWORD:
        raise CredencialesInvalidas(
            "El panel de administrador no está configurado: faltan "
            "ADMIN_USERNAME/ADMIN_PASSWORD en el backend."
        )

    if _bloqueado(usuario):
        raise DemasiadosIntentos()

    # compare_digest en ambos campos (no solo en la contraseña) para no dar
    # pistas de tiempo sobre si el usuario escrito es o no el correcto.
    #
    # Se compara en BYTES a propósito: con `str`, compare_digest lanza
    # TypeError ante cualquier carácter no ASCII, así que una contraseña con
    # tilde o eñe —perfectamente esperable acá— reventaba el login con un 500
    # en vez de un 401, y hacía imposible usar una clave con ñ.
    coincide = hmac.compare_digest(
        usuario.encode("utf-8"), settings.ADMIN_USERNAME.encode("utf-8")
    ) & hmac.compare_digest(
        contrasena.encode("utf-8"), settings.ADMIN_PASSWORD.encode("utf-8")
    )
    if not coincide:
        _intentos_fallidos.setdefault(usuario, []).append(time.time())
        raise CredencialesInvalidas()

    token = secrets.token_urlsafe(32)
    _sesiones[token] = time.time() + _TOKEN_TTL_SEGUNDOS
    return token


def cerrar_sesion(token: str) -> None:
    _sesiones.pop(token, None)


def _token_valido(token: str) -> bool:
    vence = _sesiones.get(token)
    if vence is None:
        return False
    if vence < time.time():
        _sesiones.pop(token, None)
        return False
    return True


def requiere_admin(authorization: Optional[str] = Header(default=None)) -> None:
    """Dependency de FastAPI para las rutas protegidas: exige un header
    `Authorization: Bearer <token>` con una sesión vigente."""
    token = (authorization or "").removeprefix("Bearer ").strip()
    if not token or not _token_valido(token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada. Vuelve a iniciar sesión.")
