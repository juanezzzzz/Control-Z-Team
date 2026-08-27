"""Acceso a datos vía Supabase (Postgres + JSONB).

El cliente se crea de forma perezosa (get_client) y cacheada, en vez de al
importar el módulo: así el paquete se puede importar (y testear) sin que
las credenciales de Supabase estén configuradas todavía.
"""
from functools import lru_cache
from typing import Any, Optional

from supabase import create_client, Client

from agroia.core.config import settings


@lru_cache
def get_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def insertar_producto(payload: dict[str, Any]) -> dict[str, Any]:
    """Inserta el JSON estructurado que arma el Agente 2 y devuelve el registro creado."""
    resp = get_client().table(settings.SUPABASE_TABLE_PRODUCTOS).insert(payload).execute()
    return resp.data[0]


def listar_catalogo(estado: str = "activo") -> list[dict[str, Any]]:
    """Usado por GET /api/productos/catalogo (lo consume el frontend Angular)."""
    resp = (
        get_client()
        .table(settings.SUPABASE_TABLE_PRODUCTOS)
        .select("*")
        .eq("estado", estado)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data


def buscar_productos(
    producto: Optional[str],
    ubicacion: Optional[str],
    limite: int = 5,
) -> list[dict[str, Any]]:
    """Búsqueda usada por el Agente 3 (ventas).

    Camino principal: la función RPC `buscar_productos` definida en
    `supabase_schema.sql` — ignora tildes/mayúsculas, hace coincidencia
    bidireccional ("plátano hartón" <-> "plátano") y ordena por relevancia.

    Fallback: si la RPC no existe todavía (esquema sin migrar) se cae a un
    `ilike` directo sobre la tabla, para no romper el flujo.
    """
    producto = (producto or "").strip() or None
    ubicacion = (ubicacion or "").strip() or None

    try:
        resp = get_client().rpc(
            "buscar_productos",
            {"p_producto": producto, "p_ubicacion": ubicacion, "p_limit": limite},
        ).execute()
        return resp.data or []
    except Exception:  # noqa: BLE001 — degradar con elegancia, nunca tumbar al Agente 3
        return _buscar_productos_fallback(producto, ubicacion, limite)


def _buscar_productos_fallback(
    producto: Optional[str],
    ubicacion: Optional[str],
    limite: int,
) -> list[dict[str, Any]]:
    query = (
        get_client()
        .table(settings.SUPABASE_TABLE_PRODUCTOS)
        .select("*")
        .eq("estado", "activo")
    )
    if producto:
        query = query.ilike("producto", f"%{producto}%")
    if ubicacion:
        query = query.ilike("ubicacion", f"%{ubicacion}%")
    resp = query.order("created_at", desc=True).limit(limite).execute()
    return resp.data or []
