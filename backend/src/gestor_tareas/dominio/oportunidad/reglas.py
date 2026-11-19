"""Reglas de cálculo del alta de oportunidades (fechas, nombre y formatos)."""

import calendar
from datetime import date, timedelta
from decimal import Decimal

from gestor_tareas.dominio.oportunidad.entidades import (
    ConfiguracionAltaOportunidad,
    DatosFormulario,
    SolicitudAltaOportunidad,
)


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
    return DatosFormulario(
        nombre=componer_nombre(solicitud.prj, descripcion),
        duracion=str(solicitud.duracion),
        importe=formatear_importe(solicitud.importe),
        coste=formatear_importe(solicitud.coste),
        fecha_limite=ddmmaaaa(fecha_limite(hoy, configuracion.dias_fecha_limite)),
        fecha_inicio=ddmmaaaa(mas_un_mes(hoy)),
    )
