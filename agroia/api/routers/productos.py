"""Endpoints de productos consumidos por el frontend Angular:

  GET  /api/productos/catalogo  — catálogo público de ofertas activas.
  POST /api/productos           — alta directa de una oferta desde el
                                  formulario web (sin pasar por Telegram).
"""
import logging

from fastapi import APIRouter, HTTPException, Response

from agroia.agents.agente2_estructuracion import (
    IDENTIDAD_WEB_ANONIMA,
    OfertaInvalidaError,
    estructurar_y_guardar,
)
from agroia.repositories.productos_repository import ErrorPersistencia, listar_catalogo
from agroia.schemas import OfertaExtraida, ProductoIn, ProductoOut

logger = logging.getLogger(__name__)

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
        municipio=registro.get("municipio"),
        unidad_base=registro.get("unidad_base"),
        cantidad_base=registro.get("cantidad_base"),
        precio_por_unidad_base=registro.get("precio_por_unidad_base"),
    )


@router.get("/catalogo", response_model=list[ProductoOut])
def get_catalogo():
    return [_a_producto_out(p) for p in listar_catalogo()]


@router.post("", response_model=ProductoOut, status_code=201)
def post_producto(body: ProductoIn, response: Response):
    """El formulario web arma la misma oferta que produciría el Agente 1; la
    validación, la estandarización de unidades y el insert los hace el
    Agente 2 — exactamente el mismo camino que sigue el flujo de Telegram.

    Por eso este router ya no valida campos por su cuenta: los 4 atributos
    obligatorios se exigen en un solo lugar (`validar_oferta`).
    """
    oferta = OfertaExtraida(
        producto=body.producto,
        cantidad=body.cantidad,
        unidad=body.unidad,
        precio=body.precio,
        ubicacion=body.ubicacion,
        completo=True,
    )
    try:
        resultado = estructurar_y_guardar(
            oferta,
            telegram_user_id=_identidad_web(body.telefono_contacto),
            nombre_productor=body.nombre_productor,
            telefono_contacto=body.telefono_contacto,
        )
    except OfertaInvalidaError as exc:
        raise HTTPException(status_code=400, detail=exc.errores) from exc
    except ErrorPersistencia as exc:
        # 503, no 500: la app está bien, quien no respondió fue la base de datos.
        logger.exception("Fallo de persistencia publicando desde el formulario web")
        raise HTTPException(
            status_code=503,
            detail="No se pudo guardar la oferta. Inténtalo de nuevo en un momento.",
        ) from exc

    # El productor corrigió una oferta que ya tenía: se modificó un recurso
    # existente, no se creó uno nuevo.
    if resultado.actualizada:
        response.status_code = 200

    return _a_producto_out(resultado.registro)


def _identidad_web(telefono: str | None) -> str:
    """El Agente 2 evita duplicados por productor, así que el formulario web
    necesita una identidad estable: el teléfono. Sin teléfono no hay forma de
    saber si dos publicaciones son de la misma persona, y se devuelve la
    identidad anónima — que el agente excluye de la deduplicación."""
    limpio = (telefono or "").strip()
    return f"web:{limpio}" if limpio else IDENTIDAD_WEB_ANONIMA
