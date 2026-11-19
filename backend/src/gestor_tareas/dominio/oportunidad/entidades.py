"""Alta de una oportunidad en la herramienta comercial externa.

Los valores fijos (URL, responsable, cliente, catálogos...) no viven en el código:
llegan de una configuración local que nunca se versiona.
"""

import re
from dataclasses import dataclass
from decimal import Decimal

from gestor_tareas.dominio.oportunidad.errores import SolicitudAltaOportunidadInvalidaError

MENSAJE_CODIGO_PRJ_INVALIDO = "El código debe tener el formato PRJ-XXXXX (5 dígitos)."
_PATRON_CODIGO_PRJ = re.compile(r"PRJ-\d{5}")


@dataclass(frozen=True)
class Asignacion:
    """Una línea de negocio o una comunidad con su porcentaje de asignación."""

    nombre: str
    porcentaje: str


# Nombre de la entrada del menú si la configuración local no indica otro.
NOMBRE_MENU_PREDETERMINADO = "Alta de oportunidades"


@dataclass(frozen=True)
class ConfiguracionAltaOportunidad:
    """Valores fijos del alta, leídos de la configuración local."""

    url_digital_desktop: str
    url_notion: str
    titulo_pagina_notion: str
    perfil: str
    cliente_busqueda: str
    cliente: str
    grupo: str
    tipo: str
    segmentacion: str
    fase: str
    probabilidad: str
    dias_fecha_limite: int
    tipo_servicio: str
    lineas_negocio: tuple[Asignacion, ...]
    comunidades: tuple[Asignacion, ...]
    nombre_menu: str = NOMBRE_MENU_PREDETERMINADO


@dataclass(frozen=True)
class SolicitudAltaOportunidad:
    """Campos variables que el usuario rellena en la página antes de lanzar el alta."""

    prj: str
    descripcion: str | None
    duracion: int
    importe: Decimal
    coste: Decimal

    @classmethod
    def crear(
        cls,
        prj: str,
        descripcion: str | None,
        duracion: int | None,
        importe: Decimal | None,
        coste: Decimal | None,
    ) -> "SolicitudAltaOportunidad":
        if not _PATRON_CODIGO_PRJ.fullmatch(prj or ""):
            raise SolicitudAltaOportunidadInvalidaError(MENSAJE_CODIGO_PRJ_INVALIDO)
        if duracion is None:
            raise SolicitudAltaOportunidadInvalidaError("La duración es obligatoria.")
        if duracion < 1:
            raise SolicitudAltaOportunidadInvalidaError(
                "La duración debe ser un número entero de meses mayor que cero."
            )
        importe_valido = _cantidad_valida(importe, "El importe total previsto")
        coste_valido = _cantidad_valida(coste, "El coste total previsto")
        descripcion_limpia = (descripcion or "").strip() or None
        return cls(prj, descripcion_limpia, duracion, importe_valido, coste_valido)


def _cantidad_valida(valor: Decimal | None, nombre: str) -> Decimal:
    if valor is None:
        raise SolicitudAltaOportunidadInvalidaError(f"{nombre} es obligatorio.")
    if valor < 0:
        raise SolicitudAltaOportunidadInvalidaError(f"{nombre} no puede ser negativo.")
    return valor


@dataclass(frozen=True)
class DatosFormulario:
    """Valores ya formateados que se escriben en el formulario de alta."""

    nombre: str
    duracion: str
    importe: str
    coste: str
    fecha_limite: str
    fecha_inicio: str
