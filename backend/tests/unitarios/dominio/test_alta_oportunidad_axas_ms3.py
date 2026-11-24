"""Variante AXAS MS3 del alta: código de servicio, descripción obligatoria y nombre."""

from datetime import date
from decimal import Decimal

import pytest

from gestor_tareas.dominio.oportunidad.entidades import (
    MENSAJE_CODIGO_SERVICIO_INVALIDO,
    Asignacion,
    ConfiguracionAxasMs3,
    SolicitudAltaAxasMs3,
)
from gestor_tareas.dominio.oportunidad.errores import SolicitudAltaOportunidadInvalidaError
from gestor_tareas.dominio.oportunidad.reglas import (
    componer_datos_formulario_axas_ms3,
    componer_nombre_axas_ms3,
)

CONFIGURACION_MS3 = ConfiguracionAxasMs3(
    perfil="Persona Ms3",
    responsable_busqueda=None,
    cliente_busqueda="Cliente Ms3",
    cliente="[CMS] Cliente Ms3 S.A.",
    grupo="Grupo Ms3",
    tipo="Tipo Ms3",
    responsable_operaciones="Responsable Operaciones Ejemplo",
    responsable_tecnico="Responsable Técnico Ejemplo",
    responsable_tecnico_busqueda=None,
    segmentacion="Segmentación Ms3",
    area_ms3="Área Ejemplo",
    fase="1 - Fase Ms3",
    probabilidad="50",
    dias_fecha_limite=10,
    tipo_servicio="Servicio Ms3",
    lineas_negocio=(Asignacion("Línea Ms3", "100"),),
    comunidades=(Asignacion("Comunidad X", "80"), Asignacion("Comunidad Y", "20")),
)


def _solicitud(**cambios: object) -> SolicitudAltaAxasMs3:
    datos: dict[str, object] = {
        "codigo_servicio": "AXAS0024",
        "descripcion": "Migración portal",
        "duracion": 3,
        "importe": Decimal("1000"),
        "coste": Decimal("800"),
    }
    datos.update(cambios)
    return SolicitudAltaAxasMs3.crear(**datos)  # type: ignore[arg-type]


def test_el_nombre_usa_los_dos_ultimos_caracteres_del_codigo_y_la_descripcion() -> None:
    assert (
        componer_nombre_axas_ms3("AXAS0024", "Migración portal")
        == "AXAS-MS3-EV-24-Migración portal"
    )
    assert componer_nombre_axas_ms3("XYZ9AB", "Otra cosa") == "AXAS-MS3-EV-AB-Otra cosa"


def test_la_solicitud_limpia_el_codigo_y_la_descripcion() -> None:
    solicitud = _solicitud(codigo_servicio="  AXAS0025 ", descripcion="  Migración portal  ")

    assert solicitud.codigo_servicio == "AXAS0025"
    assert solicitud.descripcion == "Migración portal"


@pytest.mark.parametrize("codigo", ["", "   ", "A", " B ", "AXAS 0024", "AX\tAS"])
def test_un_codigo_de_servicio_corto_o_con_espacios_se_rechaza(codigo: str) -> None:
    with pytest.raises(SolicitudAltaOportunidadInvalidaError) as error:
        _solicitud(codigo_servicio=codigo)

    assert str(error.value) == MENSAJE_CODIGO_SERVICIO_INVALIDO
    assert MENSAJE_CODIGO_SERVICIO_INVALIDO == (
        "El código de servicio debe tener entre 2 y 20 caracteres y no contener espacios."
    )


@pytest.mark.parametrize("descripcion", [None, "", "   "])
def test_la_descripcion_es_obligatoria(descripcion: str | None) -> None:
    with pytest.raises(SolicitudAltaOportunidadInvalidaError) as error:
        _solicitud(descripcion=descripcion)

    assert str(error.value) == "La descripción es obligatoria."


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"duracion": None}, "La duración es obligatoria."),
        ({"duracion": 0}, "La duración debe ser un número entero de meses mayor que cero."),
        ({"importe": None}, "El importe total previsto es obligatorio."),
        ({"coste": Decimal("-1")}, "El coste total previsto no puede ser negativo."),
    ],
)
def test_duracion_importe_y_coste_siguen_las_reglas_de_anes(
    cambios: dict[str, object], mensaje: str
) -> None:
    with pytest.raises(SolicitudAltaOportunidadInvalidaError) as error:
        _solicitud(**cambios)

    assert str(error.value) == mensaje


def test_los_datos_del_formulario_reutilizan_fechas_y_formatos_de_anes() -> None:
    solicitud = _solicitud(importe=Decimal("1234.5"), coste=Decimal("800"))

    datos = componer_datos_formulario_axas_ms3(solicitud, date(2026, 1, 31), CONFIGURACION_MS3)

    assert datos.nombre == "AXAS-MS3-EV-24-Migración portal"
    assert datos.observaciones == datos.nombre
    assert datos.duracion == "3"
    assert datos.importe == "1234,50"
    assert datos.coste == "800"
    assert datos.fecha_limite == "10/02/2026"  # hoy + dias_fecha_limite del bloque AXAS
    assert datos.fecha_inicio == "28/02/2026"  # hoy + 1 mes, ajustado al último día
