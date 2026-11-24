"""Reglas de cálculo del alta de oportunidades (fechas, nombre y formatos)."""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from gestor_tareas.dominio.oportunidad.entidades import (
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
    DatosFormulario,
    SolicitudAltaAxasMs3,
    SolicitudAltaOportunidad,
)

PREFIJO_NOMBRE_AXAS_MS3 = "AXAS-MS3-EV-"


def mas_un_mes(dia: date) -> date:
    """El mismo día del mes siguiente; si no existe, el último día de ese mes."""
    mes = dia.month + 1
    anio = dia.year + (mes > 12)
    mes = mes - 12 if mes > 12 else mes
    return dia.replace(year=anio, month=mes, day=min(dia.day, calendar.monthrange(anio, mes)[1]))


def fecha_limite(hoy: date, dias: int) -> date:
    return hoy + timedelta(days=dias)


def ddmmaaaa(dia: date) -> str:
    return dia.strftime("%d/%m/%Y")


def componer_nombre(prj: str, descripcion: str) -> str:
    return f"{prj} {descripcion}"


def componer_nombre_axas_ms3(codigo_servicio: str, descripcion: str) -> str:
    """Prefijo AXAS-MS3-EV-, los 2 últimos caracteres del código, guion y descripción."""
    return f"{PREFIJO_NOMBRE_AXAS_MS3}{codigo_servicio[-2:]}-{descripcion}"


def formatear_importe(valor: Decimal) -> str:
    """Sin decimales si es entero; si no, con dos decimales y coma (formato es-ES)."""
    if valor == valor.to_integral_value():
        return str(int(valor))
    return f"{valor:.2f}".replace(".", ",")


def componer_datos_formulario(
    solicitud: SolicitudAltaOportunidad,
    descripcion: str,
    hoy: date,
    configuracion: ConfiguracionAltaOportunidad,
) -> DatosFormulario:
    return _datos_formulario(
        componer_nombre(solicitud.prj, descripcion),
        solicitud.duracion,
        solicitud.importe,
        solicitud.coste,
        hoy,
        configuracion.dias_fecha_limite,
    )


def componer_datos_formulario_axas_ms3(
    solicitud: SolicitudAltaAxasMs3,
    hoy: date,
    configuracion: ConfiguracionAxasMs3,
) -> DatosFormulario:
    return _datos_formulario(
        componer_nombre_axas_ms3(solicitud.codigo_servicio, solicitud.descripcion),
        solicitud.duracion,
        solicitud.importe,
        solicitud.coste,
        hoy,
        configuracion.dias_fecha_limite,
    )


def _datos_formulario(
    nombre: str,
    duracion: int,
    importe: Decimal,
    coste: Decimal,
    hoy: date,
    dias_fecha_limite: int,
) -> DatosFormulario:
    return DatosFormulario(
        nombre=nombre,
        duracion=str(duracion),
        importe=formatear_importe(importe),
        coste=formatear_importe(coste),
        fecha_limite=ddmmaaaa(fecha_limite(hoy, dias_fecha_limite)),
        fecha_inicio=ddmmaaaa(mas_un_mes(hoy)),
    )
