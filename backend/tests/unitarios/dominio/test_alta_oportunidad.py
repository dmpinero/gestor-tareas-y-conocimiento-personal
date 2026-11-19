from datetime import date
from decimal import Decimal

import pytest

from gestor_tareas.dominio.oportunidad.entidades import (
    Asignacion,
    ConfiguracionAltaOportunidad,
    SolicitudAltaOportunidad,
)
from gestor_tareas.dominio.oportunidad.errores import SolicitudAltaOportunidadInvalidaError
from gestor_tareas.dominio.oportunidad.reglas import (
    componer_datos_formulario,
    componer_nombre,
    ddmmaaaa,
    fecha_limite,
    formatear_importe,
    mas_un_mes,
)

CONFIGURACION = ConfiguracionAltaOportunidad(
    url_digital_desktop="https://crm.ejemplo.invalid/",
    url_notion="https://notas.ejemplo.invalid/proyectos",
    titulo_pagina_notion="Proyectos de ejemplo",
    perfil="Persona Ejemplo",
    cliente_busqueda="Cliente Ejemplo",
    cliente="[CEJ] Cliente Ejemplo S.A.",
    grupo="Grupo Ejemplo",
    tipo="Tipo Ejemplo",
    segmentacion="Segmentación Ejemplo",
    fase="1 - Fase Ejemplo",
    probabilidad="50",
    dias_fecha_limite=7,
    tipo_servicio="Servicio Ejemplo",
    lineas_negocio=(Asignacion("Línea Ejemplo", "100"),),
    comunidades=(Asignacion("Comunidad A", "80"), Asignacion("Comunidad B", "20")),
)


def _solicitud(**cambios: object) -> SolicitudAltaOportunidad:
    datos: dict[str, object] = {
        "prj": "PRJ-00001",
        "descripcion": "Proyecto de prueba",
        "duracion": 2,
        "importe": Decimal("10000"),
        "coste": Decimal("8500"),
    }
    datos.update(cambios)
    return SolicitudAltaOportunidad.crear(**datos)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "prj",
    [
        "PRJ-1234",
        "PRJ-123456",
        "prj-12345",
        "PRJ12345",
        "",
        " PRJ-12345",
        "PRJ-12345 ",
        "PRJ-1234a",
        "XPRJ-12345",
        "PRJ-12345\n",
    ],
)
def test_un_codigo_prj_sin_el_formato_se_rechaza_con_el_mensaje_del_script(prj: str) -> None:
    with pytest.raises(SolicitudAltaOportunidadInvalidaError) as error:
        _solicitud(prj=prj)

    assert str(error.value) == "El código debe tener el formato PRJ-XXXXX (5 dígitos)."


def test_un_codigo_prj_con_cinco_digitos_es_valido() -> None:
    assert _solicitud(prj="PRJ-54321").prj == "PRJ-54321"


@pytest.mark.parametrize(
    ("campo", "valor", "mensaje"),
    [
        ("duracion", None, "La duración es obligatoria."),
        ("duracion", 0, "La duración debe ser un número entero de meses mayor que cero."),
        ("importe", None, "El importe total previsto es obligatorio."),
        ("importe", Decimal("-1"), "El importe total previsto no puede ser negativo."),
        ("coste", None, "El coste total previsto es obligatorio."),
        ("coste", Decimal("-0.01"), "El coste total previsto no puede ser negativo."),
    ],
)
def test_duracion_importe_y_coste_son_obligatorios(campo: str, valor: object, mensaje: str) -> None:
    with pytest.raises(SolicitudAltaOportunidadInvalidaError) as error:
        _solicitud(**{campo: valor})

    assert str(error.value) == mensaje


def test_una_descripcion_en_blanco_se_trata_como_ausente() -> None:
    assert _solicitud(descripcion="   ").descripcion is None


@pytest.mark.parametrize(
    ("hoy", "esperada"),
    [
        (date(2026, 1, 15), date(2026, 2, 15)),
        (date(2026, 1, 31), date(2026, 2, 28)),
        (date(2028, 1, 31), date(2028, 2, 29)),
        (date(2026, 12, 10), date(2027, 1, 10)),
        (date(2026, 3, 31), date(2026, 4, 30)),
        (date(2026, 12, 31), date(2027, 1, 31)),
        (date(2026, 2, 28), date(2026, 3, 28)),
    ],
)
def test_mas_un_mes_suma_un_mes_ajustando_al_ultimo_dia(hoy: date, esperada: date) -> None:
    assert mas_un_mes(hoy) == esperada


def test_la_fecha_limite_es_hoy_mas_los_dias_de_la_configuracion() -> None:
    assert fecha_limite(date(2026, 12, 28), 7) == date(2027, 1, 4)
    assert ddmmaaaa(fecha_limite(date(2026, 12, 28), 7)) == "04/01/2027"


def test_el_nombre_es_el_codigo_seguido_de_la_descripcion() -> None:
    assert componer_nombre("PRJ-00001", "Proyecto de prueba") == "PRJ-00001 Proyecto de prueba"


@pytest.mark.parametrize(
    ("importe", "texto"),
    [(Decimal("10000"), "10000"), (Decimal("10000.00"), "10000"), (Decimal("1234.5"), "1234,50")],
)
def test_los_importes_se_escriben_sin_decimales_o_con_coma(importe: Decimal, texto: str) -> None:
    assert formatear_importe(importe) == texto


def test_los_datos_del_formulario_combinan_solicitud_fechas_y_descripcion() -> None:
    datos = componer_datos_formulario(
        _solicitud(), "Proyecto de prueba", date(2026, 1, 31), CONFIGURACION
    )

    assert datos.nombre == "PRJ-00001 Proyecto de prueba"
    assert datos.duracion == "2"
    assert datos.importe == "10000"
    assert datos.coste == "8500"
    assert datos.fecha_limite == "07/02/2026"
    assert datos.fecha_inicio == "28/02/2026"
