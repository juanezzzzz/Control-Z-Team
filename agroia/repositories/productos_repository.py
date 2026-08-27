"""Acceso a datos vía Supabase (Postgres + JSONB).

El cliente se crea de forma perezosa (get_client) y cacheada, en vez de al
importar el módulo: así el paquete se puede importar (y testear) sin que
las credenciales de Supabase estén configuradas todavía.

Esta es la única capa que habla con la base de datos. Traduce los fallos de
Supabase a `ErrorPersistencia`, para que los agentes no tengan que saber
cómo luce un error de postgrest.
"""
from functools import lru_cache
from typing import Any, Optional

from supabase import Client, create_client

from agroia.core.config import settings


class ErrorPersistencia(RuntimeError):
    """No se pudo leer o escribir en la base de datos.

    El caso más frecuente en un despliegue nuevo es que la fila se rechace por
    Row Level Security: eso ocurre cuando el backend está usando la `anon key`
    en vez de la `service_role key` (ver supabase_schema.sql y el README).
    """


class ErrorDuplicado(ErrorPersistencia):
    """Ese productor ya tiene una oferta activa de ese producto.

    La levanta el índice único parcial de `supabase_schema.sql`. Es la red de
    seguridad para cuando dos mensajes del mismo campesino llegan casi
    simultáneos y ambos pasan la revisión previa de duplicados.
    """


def _es_violacion_unicidad(exc: Exception) -> bool:
    texto = str(exc).lower()
    return "23505" in texto or "duplicate key" in texto


@lru_cache
def get_client() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ErrorPersistencia(
            "Faltan SUPABASE_URL o SUPABASE_KEY. Configúralas en el .env "
            "(local) o en las variables de entorno del despliegue."
        )
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def _tabla():
    return get_client().table(settings.SUPABASE_TABLE_PRODUCTOS)


def _primera_fila(resp: Any, operacion: str) -> dict[str, Any]:
    """Supabase no lanza excepción cuando RLS bloquea una escritura: devuelve
    `data` vacío y un 200. Sin esta guarda, el `data[0]` de siempre revienta
    con un IndexError que no dice nada útil."""
    datos = getattr(resp, "data", None) or []
    if not datos:
        raise ErrorPersistencia(
            f"Supabase no devolvió ninguna fila al {operacion}. Casi siempre es "
            "Row Level Security bloqueando la operación: verifica que "
            "SUPABASE_KEY sea la 'service_role key' del proyecto, no la 'anon key'."
        )
    return datos[0]


def insertar_producto(payload: dict[str, Any]) -> dict[str, Any]:
    """Inserta el JSON estructurado que arma el Agente 2 y devuelve el registro creado."""
    try:
        resp = _tabla().insert(payload).execute()
    except ErrorPersistencia:
        raise
    except Exception as exc:  # errores de red, auth, columna inexistente…
        if _es_violacion_unicidad(exc):
            raise ErrorDuplicado(
                "Ese productor ya tiene una oferta activa de ese producto."
            ) from exc
        raise ErrorPersistencia(f"Falló la inserción en Supabase: {exc}") from exc
    return _primera_fila(resp, "insertar la oferta")


def actualizar_producto(producto_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Reemplaza los datos de una oferta existente. Lo usa el Agente 2 cuando
    el mismo productor vuelve a publicar el mismo producto."""
    try:
        resp = _tabla().update(payload).eq("id", producto_id).execute()
    except ErrorPersistencia:
        raise
    except Exception as exc:
        raise ErrorPersistencia(f"Falló la actualización en Supabase: {exc}") from exc
    return _primera_fila(resp, "actualizar la oferta")


def buscar_oferta_activa(telegram_user_id: str, producto: str) -> Optional[dict[str, Any]]:
    """Oferta activa que ese mismo productor ya tiene publicada de ese producto.

    Es la que permite al Agente 2 actualizar en vez de duplicar. Devuelve None
    si no hay ninguna, y también si la consulta falla: no poder revisar
    duplicados nunca debe impedir publicar una oferta nueva.
    """
    try:
        resp = (
            _tabla()
            .select("*")
            .eq("telegram_user_id", telegram_user_id)
            .eq("producto", producto)
            .eq("estado", "activo")
            .limit(1)
            .execute()
        )
    except Exception:
        return None
    datos = getattr(resp, "data", None) or []
    return datos[0] if datos else None


def listar_catalogo(estado: str = "activo") -> list[dict[str, Any]]:
    """Usado por GET /api/productos/catalogo (lo consume el frontend Angular)."""
    try:
        resp = (
            _tabla()
            .select("*")
            .eq("estado", estado)
            .order("created_at", desc=True)
            .execute()
        )
    except ErrorPersistencia:
        raise
    except Exception as exc:
        raise ErrorPersistencia(f"Falló la consulta del catálogo: {exc}") from exc
    return getattr(resp, "data", None) or []


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
        return getattr(resp, "data", None) or []
    except ErrorPersistencia:
        raise
    except Exception:  # noqa: BLE001 — RPC ausente (esquema sin migrar) u otro fallo: probar el camino simple
        return _buscar_productos_fallback(producto, ubicacion, limite)


def _buscar_productos_fallback(
    producto: Optional[str],
    ubicacion: Optional[str],
    limite: int,
) -> list[dict[str, Any]]:
    """Sin la RPC: `ilike` directo sobre la tabla (sensible a tildes, sin
    ranking). Suficiente para no romper el Agente 3 mientras se migra el
    esquema."""
    query = _tabla().select("*").eq("estado", "activo")
    if producto:
        query = query.ilike("producto", f"%{producto}%")
    if ubicacion:
        query = query.ilike("ubicacion", f"%{ubicacion}%")
    try:
        resp = query.order("created_at", desc=True).limit(limite).execute()
    except ErrorPersistencia:
        raise
    except Exception as exc:
        raise ErrorPersistencia(f"Falló la búsqueda de productos: {exc}") from exc
    return getattr(resp, "data", None) or []
