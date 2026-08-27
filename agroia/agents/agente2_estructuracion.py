"""Agente 2: Procesamiento y Estructuración de la Base de Datos.

Toma la oferta ya validada por el Agente 1, estandariza el formato y la
inserta en Supabase, dejándola disponible de inmediato para el catálogo
en Angular (vía Realtime) y para las búsquedas del Agente 3.
"""
from typing import Any

from agroia.repositories.productos_repository import insertar_producto
from agroia.schemas import OfertaExtraida


def estructurar_y_guardar(
    oferta: OfertaExtraida,
    telegram_user_id: str,
    nombre_productor: str | None = None,
    telefono_contacto: str | None = None,
) -> dict[str, Any]:
    payload = {
        "telegram_user_id": telegram_user_id,
        "nombre_productor": nombre_productor,
        "telefono_contacto": telefono_contacto,
        "producto": (oferta.producto or "").strip().lower(),
        "cantidad": oferta.cantidad,
        "unidad": (oferta.unidad or "").strip().lower() or None,
        "precio": oferta.precio,
        "ubicacion": (oferta.ubicacion or "").strip().title(),
        "estado": "activo",
        "raw_json": oferta.model_dump(),
    }
    return insertar_producto(payload)
