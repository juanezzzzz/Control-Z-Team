"""Diagnóstico de la conexión con Supabase.

Ejecutar desde la raíz del proyecto, con el .env ya lleno:

    python -m scripts.verificar_supabase

Revisa, en orden, todo lo que puede fallar al conectar — y para cada fallo
dice qué hacer. Es de solo diagnóstico salvo el último paso, que escribe una
fila de prueba y la borra enseguida.

Nunca imprime el valor de una credencial.
"""
import base64
import binascii
import json
import sys

from agroia.core.config import settings

MARCA_PRUEBA = "__verificacion__"

OK = "[OK]  "
MAL = "[MAL] "
AVISO = "[!]   "


def _rol_de_la_clave(clave: str) -> str | None:
    """Lee el claim `role` de una clave de Supabase sin validar la firma.

    Las claves clásicas son JWT con {"role": "anon"} o {"role": "service_role"};
    las nuevas empiezan por sb_publishable_ / sb_secret_. Solo nos interesa
    distinguir "puede escribir" de "no puede", para avisar antes de que el
    error aparezca como una inserción que se pierde en silencio.
    """
    if clave.startswith("sb_secret_"):
        return "service_role"
    if clave.startswith("sb_publishable_"):
        return "anon"

    partes = clave.split(".")
    if len(partes) != 3:
        return None
    try:
        carga = partes[1] + "=" * (-len(partes[1]) % 4)  # repone el padding base64
        return json.loads(base64.urlsafe_b64decode(carga)).get("role")
    except (binascii.Error, ValueError, UnicodeDecodeError):
        return None


def paso_1_variables() -> bool:
    print("\n1. Variables de entorno")
    ok = True
    for nombre in ("SUPABASE_URL", "SUPABASE_KEY"):
        if getattr(settings, nombre):
            print(f"{OK}{nombre} está definida")
        else:
            print(f"{MAL}{nombre} está vacía o no existe")
            ok = False
    if not ok:
        print("\n      -> Copia .env.example a .env y llena esas dos variables.")
        print("         Supabase: Project Settings -> API")
    return ok


def paso_2_url() -> bool:
    print("\n2. Formato de SUPABASE_URL")
    url = settings.SUPABASE_URL
    if not url.startswith("https://"):
        print(f"{MAL}Debe empezar por https:// (la tuya empieza por '{url[:8]}...')")
        return False
    if not url.rstrip("/").endswith(".supabase.co"):
        print(f"{AVISO}No termina en .supabase.co — revisa que sea el 'Project URL'")
        print("      y no la URL del panel (app.supabase.com/project/...).")
        return False
    print(f"{OK}Se ve bien: https://...{url[-20:]}")
    return True


def paso_3_tipo_de_clave() -> bool:
    print("\n3. Tipo de SUPABASE_KEY")
    rol = _rol_de_la_clave(settings.SUPABASE_KEY)

    if rol == "service_role":
        print(f"{OK}Es la service_role — el backend puede escribir")
        return True
    if rol == "anon":
        print(f"{MAL}Es la clave ANON. Con RLS activo NO puede escribir:")
        print("      los inserts fallan devolviendo 0 filas, sin lanzar error.")
        print("\n      -> Supabase -> Project Settings -> API -> copia la clave")
        print("         marcada 'service_role' / 'secret'.")
        return False

    print(f"{AVISO}No pude identificar el tipo de clave. Sigo, pero si la")
    print("      escritura falla más abajo, es casi seguro que es la anon.")
    return True


def paso_4_conexion_y_tabla() -> bool:
    print(f"\n4. Conexión y tabla '{settings.SUPABASE_TABLE_PRODUCTOS}'")
    from agroia.repositories.productos_repository import get_client

    try:
        get_client().table(settings.SUPABASE_TABLE_PRODUCTOS).select("id").limit(1).execute()
    except Exception as exc:
        texto = str(exc).lower()
        print(f"{MAL}{exc}")
        if "does not exist" in texto or "pgrst205" in texto:
            print("\n      -> La tabla no existe. Abre el SQL Editor de Supabase,")
            print("         pega supabase_schema.sql completo y ejecútalo.")
        elif "invalid api key" in texto or "jwt" in texto:
            print("\n      -> La clave no es válida para este proyecto. Verifica que")
            print("         SUPABASE_URL y SUPABASE_KEY sean del MISMO proyecto.")
        else:
            print("\n      -> Revisa tu conexión a internet y que el proyecto de")
            print("         Supabase no esté pausado (se pausa solo tras 7 días).")
        return False

    print(f"{OK}Conectado y la tabla existe")
    return True


def paso_5_columnas_del_agente2() -> bool:
    print("\n5. Columnas que agrega el Agente 2")
    from agroia.repositories.productos_repository import get_client

    columnas = "unidad_original,categoria_unidad,unidad_base,cantidad_base,precio_por_unidad_base,municipio"
    try:
        get_client().table(settings.SUPABASE_TABLE_PRODUCTOS).select(columnas).limit(1).execute()
    except Exception as exc:
        print(f"{MAL}Faltan columnas: {exc}")
        print("\n      -> Vuelve a ejecutar supabase_schema.sql completo. Trae los")
        print("         'alter table ... add column if not exists' y es idempotente.")
        return False

    print(f"{OK}Las 6 columnas estandarizadas están presentes")
    return True


def paso_6_escritura() -> bool:
    """La prueba de verdad: RLS solo se manifiesta al escribir."""
    print("\n6. Permiso de escritura (inserta una fila de prueba y la borra)")
    from agroia.repositories.productos_repository import ErrorPersistencia, get_client

    tabla = get_client().table(settings.SUPABASE_TABLE_PRODUCTOS)
    fila = {
        "telegram_user_id": MARCA_PRUEBA,
        "producto": MARCA_PRUEBA,
        "cantidad": 1,
        "precio": 1,
        "ubicacion": "Yopal",
        "estado": "inactivo",  # inactivo: no aparece en el catálogo aunque falle el borrado
    }

    try:
        resp = tabla.insert(fila).execute()
    except Exception as exc:
        print(f"{MAL}El insert lanzó un error: {exc}")
        return False

    if not (getattr(resp, "data", None) or []):
        print(f"{MAL}El insert devolvió 0 filas — Row Level Security lo bloqueó.")
        print("\n      -> Estás usando la clave anon. Cámbiala por la service_role.")
        return False

    creado = resp.data[0]
    print(f"{OK}Escritura permitida (fila de prueba {str(creado['id'])[:8]}...)")

    try:
        tabla.delete().eq("telegram_user_id", MARCA_PRUEBA).execute()
        print(f"{OK}Fila de prueba borrada")
    except Exception as exc:
        print(f"{AVISO}No pude borrar la fila de prueba: {exc}")
        print(f"      Bórrala a mano: telegram_user_id = '{MARCA_PRUEBA}'")

    return True


def main() -> int:
    print("=" * 62)
    print("  Verificación de la conexión con Supabase — AgroIA Casanare")
    print("=" * 62)

    # Cada paso depende del anterior: no tiene sentido probar la escritura
    # si ni siquiera hay credenciales.
    for paso in (
        paso_1_variables,
        paso_2_url,
        paso_3_tipo_de_clave,
        paso_4_conexion_y_tabla,
        paso_5_columnas_del_agente2,
        paso_6_escritura,
    ):
        if not paso():
            print("\n" + "=" * 62)
            print("  Se detuvo acá. Arregla lo de arriba y vuelve a ejecutar.")
            print("=" * 62)
            return 1

    print("\n" + "=" * 62)
    print("  TODO LISTO — el Agente 2 puede guardar ofertas en Supabase.")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    sys.exit(main())
