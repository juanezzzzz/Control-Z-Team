"""Endpoints del panel de administrador (`/admin` en el frontend):

  POST   /api/admin/login                     — usuario/contraseña -> token.
  GET    /api/admin/productos                 — todas las ofertas (cualquier estado).
  PATCH  /api/admin/productos/{id}/estado      — moderar: activo | vendido | inactivo.
  DELETE /api/admin/productos/{id}             — borrado permanente.

Login sin autenticación previa; las otras tres exigen un token vigente (ver
`agroia.core.admin_auth.requiere_admin`).
"""
import logging

from fastapi import APIRouter, Depends, HTTPException

from agroia.core.admin_auth import CredencialesInvalidas, DemasiadosIntentos, iniciar_sesion, requiere_admin
from agroia.repositories.productos_repository import (
    ErrorPersistencia,
    actualizar_producto,
    eliminar_producto,
    listar_todos,
)
from agroia.schemas import CambiarEstadoIn, LoginIn, LoginOut, ProductoOut, a_producto_out

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])

ESTADOS_VALIDOS = {"activo", "vendido", "inactivo"}


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    try:
        token = iniciar_sesion(body.usuario, body.contrasena)
    except DemasiadosIntentos as exc:
        raise HTTPException(
            status_code=429,
            detail="Demasiados intentos fallidos. Espera unos minutos y vuelve a intentar.",
        ) from exc
    except CredencialesInvalidas as exc:
        raise HTTPException(status_code=401, detail=str(exc) or "Usuario o contraseña incorrectos.") from exc
    return LoginOut(token=token)


@router.get("/productos", response_model=list[ProductoOut], dependencies=[Depends(requiere_admin)])
def listar():
    """A diferencia del catálogo público, trae ofertas en cualquier estado
    (activo, vendido, inactivo) para poder moderarlas."""
    return [a_producto_out(p) for p in listar_todos()]


@router.patch(
    "/productos/{producto_id}/estado",
    response_model=ProductoOut,
    dependencies=[Depends(requiere_admin)],
)
def cambiar_estado(producto_id: str, body: CambiarEstadoIn):
    if body.estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Usa uno de: {', '.join(sorted(ESTADOS_VALIDOS))}.",
        )
    try:
        registro = actualizar_producto(producto_id, {"estado": body.estado})
    except ErrorPersistencia as exc:
        logger.exception("Fallo cambiando el estado de %s desde el panel admin", producto_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return a_producto_out(registro)


@router.delete("/productos/{producto_id}", status_code=204, dependencies=[Depends(requiere_admin)])
def eliminar(producto_id: str):
    try:
        eliminar_producto(producto_id)
    except ErrorPersistencia as exc:
        logger.exception("Fallo eliminando %s desde el panel admin", producto_id)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
