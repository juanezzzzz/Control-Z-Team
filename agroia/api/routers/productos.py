"""Endpoints de productos consumidos por el frontend Angular:

  GET  /api/productos/catalogo  — catálogo público de ofertas activas.
  POST /api/productos           — alta directa de una oferta desde el
                                  formulario web (sin pasar por Telegram).
"""
from fastapi import APIRouter, HTTPException

from agroia.agents.agente2_estructuracion import estructurar_y_guardar
from agroia.repositories.productos_repository import listar_catalogo
from agroia.schemas import OfertaExtraida, ProductoIn, ProductoOut

router = APIRouter(prefix="/api/productos", tags=["productos"])


def _a_producto_out(registro: dict) -> ProductoOut:
    return ProductoOut(
        id=str(registro["id"]),
        producto=registro["producto"],
        cantidad=registro.get("cantidad"),
        unidad=registro.get("unidad"),
        precio=registro.get("precio"),
        ubicacion=registro.get("ubicacion"),
        telefono_contacto=registro.get("telefono_contacto"),
        estado=registro.get("estado", "activo"),
    )


@router.get("/catalogo", response_model=list[ProductoOut])
def get_catalogo():
    return [_a_producto_out(p) for p in listar_catalogo()]


@router.post("", response_model=ProductoOut, status_code=201)
def post_producto(body: ProductoIn):
    """El formulario web arma la misma oferta que produciría el Agente 1;
    la normalización + insert la hace el Agente 2, igual que en el flujo
    de Telegram."""
    if not body.producto.strip() or not body.ubicacion.strip():
        raise HTTPException(status_code=400, detail="'producto' y 'ubicacion' son obligatorios.")

    oferta = OfertaExtraida(
        producto=body.producto,
        cantidad=body.cantidad,
        unidad=body.unidad,
        precio=body.precio,
        ubicacion=body.ubicacion,
        completo=True,
    )
    registro = estructurar_y_guardar(
        oferta,
        telegram_user_id="web",
        nombre_productor=(body.nombre_productor or "").strip() or None,
        telefono_contacto=(body.telefono_contacto or "").strip() or None,
    )
    return _a_producto_out(registro)
