"""Agente 2: Procesamiento y Estructuración de la Base de Datos.

Sección 3 del documento de arquitectura:

  Entrada       Datos consolidados y validados provenientes del Agente 1.
  Procesamiento Mapea los atributos extraídos hacia el esquema de la base de
                datos, estandariza unidades de medida y genera el objeto
                JSON final.
  Salida        Ejecuta la inserción del documento JSON en la base de datos,
                dejando la información inmediatamente disponible para la
                vista en Angular.

Esas tres etapas son las tres funciones públicas de este módulo
(`validar_oferta`, `construir_documento`, `estructurar_y_guardar`). Solo la
última toca la base de datos: las dos primeras son puras, así que la lógica
de estandarización se prueba sin Supabase ni el LLM.

El agente no sabe nada de FastAPI ni de Telegram — recibe una
`OfertaExtraida` y devuelve el registro insertado. Las tablas de
equivalencias viven en `agroia/agents/normalizacion.py`.
"""
import logging
from dataclasses import dataclass
from typing import Any

from agroia.agents.normalizacion import (
    normalizar_producto,
    normalizar_ubicacion,
    normalizar_unidad,
)
from agroia.repositories.productos_repository import (
    ErrorDuplicado,
    actualizar_producto,
    buscar_oferta_activa,
    insertar_producto,
)
from agroia.schemas import OfertaExtraida

logger = logging.getLogger(__name__)

# Los mismos 4 atributos obligatorios que exige el Agente 1 (sección 3 del
# documento). Se revalidan aquí porque el formulario web entra directo por
# POST /api/productos, sin pasar por el Agente 1.
CAMPOS_OBLIGATORIOS = ("producto", "cantidad", "precio", "ubicacion")

# Topes de sensatez, no de negocio: existen para atrapar un dedo pegado en el
# teclado o una transcripción de voz que salió mal ("dos mil" -> 2000000000),
# no para limitar a un productor grande.
CANTIDAD_MAXIMA = 1_000_000
PRECIO_MAXIMO = 100_000_000

# Identidad que usa el formulario web cuando no dejó teléfono: al no ser un
# productor identificable, sus ofertas nunca se deduplican entre sí.
IDENTIDAD_WEB_ANONIMA = "web"


@dataclass(frozen=True)
class ResultadoEstructuracion:
    """Lo que devuelve el Agente 2 al terminar.

    `actualizada` distingue "publiqué tu oferta" de "corregí la que ya
    tenías": el webhook usa ese dato para responderle al campesino lo que de
    verdad pasó, y el router para devolver 201 (creado) o 200 (actualizado).
    """

    registro: dict[str, Any]
    actualizada: bool


class OfertaInvalidaError(ValueError):
    """La oferta no cumple los atributos obligatorios.

    Se levanta antes de tocar la base de datos. El router la traduce a un
    HTTP 400 y el webhook la convierte en un mensaje de vuelta al productor,
    así que `errores` está redactado para que lo lea una persona.
    """

    def __init__(self, errores: list[str]):
        self.errores = errores
        super().__init__(" ".join(errores))


def validar_oferta(oferta: OfertaExtraida) -> list[str]:
    """Etapa 1 — entrada. Devuelve la lista de problemas (vacía si está bien).

    Devuelve todos los errores juntos, en vez de abortar en el primero, para
    poder preguntarle al productor una sola vez por todo lo que falta.
    """
    errores: list[str] = []

    if not (oferta.producto or "").strip():
        errores.append("Falta el producto.")
    if not (oferta.ubicacion or "").strip():
        errores.append("Falta la ubicación.")

    if oferta.cantidad is None:
        errores.append("Falta la cantidad.")
    elif oferta.cantidad <= 0:
        errores.append("La cantidad debe ser mayor que cero.")
    elif oferta.cantidad > CANTIDAD_MAXIMA:
        errores.append(f"La cantidad parece equivocada (más de {CANTIDAD_MAXIMA:,}).")

    if oferta.precio is None:
        errores.append("Falta el precio.")
    elif oferta.precio <= 0:
        errores.append("El precio debe ser mayor que cero.")
    elif oferta.precio > PRECIO_MAXIMO:
        errores.append(f"El precio parece equivocado (más de ${PRECIO_MAXIMO:,}).")

    return errores


def construir_documento(
    oferta: OfertaExtraida,
    telegram_user_id: str,
    nombre_productor: str | None = None,
    telefono_contacto: str | None = None,
) -> dict[str, Any]:
    """Etapa 2 — procesamiento. Arma el JSON final con el esquema de la tabla
    `productos`. Asume que `validar_oferta` ya pasó.

    Además de mapear y estandarizar, calcula los campos derivados
    (`cantidad_base`, `precio_por_unidad_base`): son los que le permiten a
    Angular mostrar "$2.000/kg" y comparar dos ofertas escritas en unidades
    distintas — algo que el frontend no puede derivar solo, porque la tabla
    de equivalencias vive acá. Lo que sí puede calcular por su cuenta
    (cantidad × precio) no se guarda, para no duplicar estado.
    """
    unidad = normalizar_unidad(oferta.unidad)
    unidad_original = (oferta.unidad or "").strip() or None
    ubicacion, municipio = normalizar_ubicacion(oferta.ubicacion or "")

    cantidad = float(oferta.cantidad)
    precio = float(oferta.precio)

    documento: dict[str, Any] = {
        "telegram_user_id": telegram_user_id,
        "nombre_productor": (nombre_productor or "").strip() or None,
        "telefono_contacto": (telefono_contacto or "").strip() or None,
        "producto": normalizar_producto(oferta.producto or ""),
        "cantidad": cantidad,
        # `unidad` guarda la forma canónica ("arroba"); `unidad_original`
        # conserva lo que dijo el productor ("arrobitas") para poder auditar
        # después qué sinónimos falta agregar a la tabla.
        "unidad": unidad.canonica if unidad else unidad_original,
        "unidad_original": unidad_original,
        "categoria_unidad": unidad.categoria if unidad else None,
        "precio": precio,
        "ubicacion": ubicacion,
        "municipio": municipio,
        "estado": "activo",
        "raw_json": oferta.model_dump(),
    }

    # Solo se convierte cuando la equivalencia es fija. Un "bulto" o un
    # "racimo" no pesan siempre lo mismo: ahí se dejan los derivados en null
    # y el catálogo muestra el precio tal como lo dijo el productor.
    if unidad is not None and unidad.factor_base is not None:
        documento["unidad_base"] = unidad.base
        documento["cantidad_base"] = round(cantidad * unidad.factor_base, 3)
        documento["precio_por_unidad_base"] = round(precio / unidad.factor_base, 2)
    else:
        documento["unidad_base"] = None
        documento["cantidad_base"] = None
        documento["precio_por_unidad_base"] = None

    return documento


def estructurar_y_guardar(
    oferta: OfertaExtraida,
    telegram_user_id: str,
    nombre_productor: str | None = None,
    telefono_contacto: str | None = None,
) -> ResultadoEstructuracion:
    """Etapa 3 — salida. Punto de entrada del Agente 2: valida, estructura y
    persiste. El registro queda visible de inmediato para el catálogo en
    Angular (vía Realtime) y para las búsquedas del Agente 3.

    Si ese productor ya tiene una oferta activa del mismo producto, la
    **actualiza** en vez de crear otra fila: un campesino que reenvía su
    oferta está corrigiendo el precio o la cantidad, no publicando algo
    nuevo, y un catálogo lleno de duplicados es inservible para el comprador.

    Levanta `OfertaInvalidaError` si la oferta no está completa, y
    `ErrorPersistencia` si la base de datos rechaza la escritura.
    """
    errores = validar_oferta(oferta)
    if errores:
        logger.info("Oferta rechazada de %s: %s", telegram_user_id, errores)
        raise OfertaInvalidaError(errores)

    documento = construir_documento(
        oferta,
        telegram_user_id=telegram_user_id,
        nombre_productor=nombre_productor,
        telefono_contacto=telefono_contacto,
    )
    logger.info(
        "Estructurada oferta de %s: %s %s %s en %s",
        telegram_user_id, documento["cantidad"], documento["unidad"],
        documento["producto"], documento["ubicacion"],
    )

    deduplicable = telegram_user_id != IDENTIDAD_WEB_ANONIMA
    if deduplicable:
        existente = buscar_oferta_activa(telegram_user_id, documento["producto"])
        if existente:
            return _actualizar(str(existente["id"]), documento)

    try:
        return ResultadoEstructuracion(insertar_producto(documento), actualizada=False)
    except ErrorDuplicado:
        # Carrera: entre la revisión de arriba y este insert entró otro mensaje
        # del mismo productor. El índice único de la BD lo atajó; se resuelve
        # como lo que era, una corrección de la misma oferta.
        if not deduplicable:
            raise
        logger.info("Insert duplicado detectado para %s; se actualiza", telegram_user_id)
        existente = buscar_oferta_activa(telegram_user_id, documento["producto"])
        if not existente:
            raise
        return _actualizar(str(existente["id"]), documento)


def _actualizar(producto_id: str, documento: dict[str, Any]) -> ResultadoEstructuracion:
    logger.info("Actualizando la oferta %s en vez de duplicarla", producto_id)
    return ResultadoEstructuracion(actualizar_producto(producto_id, documento), actualizada=True)
