"""API de la variante AXAS MS3 del alta, con un navegador simulado.

Comparte con ANES el ciclo de vida, las preguntas, el cerrojo de una ejecución a
la vez y los endpoints de estado, respuesta y captura.
"""

import threading

from gestor_tareas.dominio.oportunidad.entidades import MENSAJE_CODIGO_SERVICIO_INVALIDO
from tests.unitarios.interfaces.alta_oportunidades_dobles import (
    CAPTURA_PNG,
    CONFIGURACION,
    CONFIGURACION_CON_MS3,
    CONFIGURACION_MS3,
    NOMBRE_MS3,
    RUTA,
    RUTA_MS3,
    SOLICITUD,
    SOLICITUD_MS3,
    FuenteFija,
    FuenteRota,
    esperar_fin,
    esperar_pregunta,
    montar_cliente,
    responder,
)

MENSAJE_SIN_BLOQUE = (
    "La configuración local no tiene el bloque 'axas_ms3'. Añádelo a partir de "
    "config/alta_oportunidad.ejemplo.json (consulta el README)."
)


def test_la_configuracion_ms3_muestra_sus_valores_fijos_y_sus_fechas() -> None:
    cliente, _, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))

    respuesta = cliente.get(f"{RUTA_MS3}/configuracion")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "valores": {
            "perfil": "Persona Ms3",
            "cliente": "[CMS] Cliente Ms3 S.A.",
            "grupo": "Grupo Ms3",
            "tipo": "Tipo Ms3",
            "segmentacion": "Segmentación Ms3",
            "fase": "1 - Fase Ms3",
            "probabilidad": "60",
            "dias_fecha_limite": 10,
            "tipo_servicio": "Servicio Ms3",
            "lineas_negocio": [{"nombre": "Línea Ms3", "porcentaje": "100"}],
            "comunidades": [
                {"nombre": "Comunidad X", "porcentaje": "80"},
                {"nombre": "Comunidad Y", "porcentaje": "20"},
            ],
            "responsable_operaciones": "Responsable Operaciones Ejemplo",
            "responsable_tecnico": "Responsable Técnico Ejemplo",
            "area_ms3": "Área Ejemplo",
        },
        "error": None,
        "fecha_limite": "10/02/2026",  # 31/01/2026 + 10 días del bloque AXAS MS3
        "fecha_inicio": "28/02/2026",
        "nombre_menu": "Oportunidades AXAS MS3",
    }


def test_sin_bloque_ms3_la_configuracion_explica_el_error_y_anes_sigue_igual() -> None:
    cliente, _, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION))

    cuerpo = cliente.get(f"{RUTA_MS3}/configuracion").json()
    anes = cliente.get(f"{RUTA}/configuracion").json()

    assert cuerpo == {
        "valores": None,
        "error": MENSAJE_SIN_BLOQUE,
        "fecha_limite": None,
        "fecha_inicio": "28/02/2026",
        "nombre_menu": "Oportunidades AXAS MS3",
    }
    assert anes["error"] is None
    assert anes["valores"]["perfil"] == "Persona Ejemplo"


def test_sin_archivo_de_configuracion_ms3_da_el_mismo_error_que_anes() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteRota())

    resumen = cliente.get(f"{RUTA_MS3}/configuracion").json()
    lanzada = cliente.post(f"{RUTA_MS3}/ejecucion", json=SOLICITUD_MS3)

    assert resumen["error"] == "No existe el archivo de configuración /config/x.json."
    assert resumen["valores"] is None
    assert lanzada.status_code == 503
    assert lanzada.json() == {
        "detalle": "No se puede lanzar el alta: No existe el archivo de configuración "
        "/config/x.json."
    }
    assert navegadores == []


def test_sin_bloque_ms3_no_se_puede_lanzar_la_variante_pero_si_anes() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION))
    with cliente:
        respuesta = cliente.post(f"{RUTA_MS3}/ejecucion", json=SOLICITUD_MS3)

        assert respuesta.status_code == 503
        assert respuesta.json() == {"detalle": f"No se puede lanzar el alta: {MENSAJE_SIN_BLOQUE}"}
        assert navegadores == []
        assert cliente.get(f"{RUTA}/ejecucion").status_code == 404

        assert cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code == 201
        responder(cliente, esperar_pregunta(cliente, "guardar"), "no_guardar")
        esperar_fin(cliente)


def test_un_codigo_de_servicio_invalido_da_422_sin_abrir_el_navegador() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))

    respuesta = cliente.post(
        f"{RUTA_MS3}/ejecucion", json={**SOLICITUD_MS3, "codigo_servicio": "AX 24"}
    )

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_CODIGO_SERVICIO_INVALIDO}
    assert navegadores == []


def test_un_codigo_de_servicio_de_mas_de_20_caracteres_da_422_como_el_catalogo() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))

    respuesta = cliente.post(
        f"{RUTA_MS3}/ejecucion", json={**SOLICITUD_MS3, "codigo_servicio": "A" * 21}
    )

    assert respuesta.status_code == 422
    assert respuesta.json() == {"detalle": MENSAJE_CODIGO_SERVICIO_INVALIDO}
    assert navegadores == []
    ok = cliente.post(f"{RUTA_MS3}/ejecucion", json={**SOLICITUD_MS3, "codigo_servicio": "A" * 20})
    assert ok.status_code == 201
    responder(cliente, esperar_pregunta(cliente, "guardar"), "no_guardar")
    esperar_fin(cliente)


def test_la_descripcion_es_obligatoria_en_la_api() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))

    for descripcion in (None, "  "):
        respuesta = cliente.post(
            f"{RUTA_MS3}/ejecucion", json={**SOLICITUD_MS3, "descripcion": descripcion}
        )

        assert respuesta.status_code == 422
        assert respuesta.json() == {"detalle": "La descripción es obligatoria."}
    sin_campo = {k: v for k, v in SOLICITUD_MS3.items() if k != "descripcion"}
    assert cliente.post(f"{RUTA_MS3}/ejecucion", json=sin_campo).json() == {
        "detalle": "La descripción es obligatoria."
    }
    assert navegadores == []


def test_el_alta_ms3_completa_usa_su_perfil_su_cliente_y_su_relleno() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))
    with cliente:
        lanzada = cliente.post(f"{RUTA_MS3}/ejecucion", json=SOLICITUD_MS3)

        assert lanzada.status_code == 201
        assert lanzada.json()["prj"] == NOMBRE_MS3
        assert lanzada.json()["estado"] == "en_curso"
        estado = esperar_pregunta(cliente, "guardar")  # estado compartido con ANES
        responder(cliente, estado, "guardar")
        final = esperar_fin(cliente)

        navegador = navegadores[0]
        assert final["estado"] == "guardada"
        assert final["prj"] == NOMBRE_MS3
        assert f"Nombre de la oportunidad: {NOMBRE_MS3}" in final["pasos"]
        assert navegador.llamadas == [
            "abrir",
            "iniciar_sesion",
            "cambiar_perfil",
            "existe_oportunidad",
            "rellenar_axas_ms3",
            "resumen_formulario",
            "guardar",
            "cerrar",
        ]  # sin buscar la descripción en Notion
        assert navegador.perfil == "Persona Ms3"
        assert navegador.busqueda_duplicado == (
            "[CMS] Cliente Ms3 S.A.",
            "Cliente Ms3",
            NOMBRE_MS3,
        )
        assert navegador.configuracion_ms3 == CONFIGURACION_MS3
        assert navegador.datos is not None
        assert navegador.datos.nombre == NOMBRE_MS3
        assert navegador.datos.observaciones == NOMBRE_MS3
        assert navegador.datos.fecha_limite == "10/02/2026"
        assert navegador.datos.importe == "10000"
        assert cliente.get(f"{RUTA}/ejecucion/captura").content == CAPTURA_PNG


def test_si_ya_existe_una_oportunidad_con_el_nombre_completo_pregunta() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3), existe=True)
    with cliente:
        cliente.post(f"{RUTA_MS3}/ejecucion", json=SOLICITUD_MS3)

        estado = esperar_pregunta(cliente, "duplicado")
        assert estado["pregunta"]["mensaje"] == (
            f"Ya existe una oportunidad con {NOMBRE_MS3}. ¿Crear otra igualmente?"
        )
        responder(cliente, estado, "no")
        final = esperar_fin(cliente)

        assert final["estado"] == "no_guardada"
        assert final["mensaje_final"] == "No se ha creado ninguna oportunidad."
        assert "rellenar_axas_ms3" not in navegadores[0].llamadas


def test_solo_hay_un_alta_a_la_vez_entre_anes_y_ms3() -> None:
    bloqueo = threading.Event()
    cliente, _, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3), bloquear_abrir=bloqueo)
    with cliente:
        assert cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code == 201

        respuesta = cliente.post(f"{RUTA_MS3}/ejecucion", json=SOLICITUD_MS3)

        assert respuesta.status_code == 409
        assert respuesta.json() == {
            "detalle": "Ya hay un alta de oportunidad en curso; espera a que termine."
        }
        bloqueo.set()
        responder(cliente, esperar_pregunta(cliente, "guardar"), "no_guardar")
        esperar_fin(cliente)


def test_anes_sigue_usando_su_perfil_y_busca_el_prj_en_su_cliente() -> None:
    cliente, navegadores, _ = montar_cliente(fuente=FuenteFija(CONFIGURACION_CON_MS3))
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "guardar")
        responder(cliente, estado, "no_guardar")
        final = esperar_fin(cliente)

        navegador = navegadores[0]
        assert final["prj"] == "PRJ-00001"
        assert navegador.perfil == "Persona Ejemplo"
        assert navegador.busqueda_duplicado == (
            "[CEJ] Cliente Ejemplo S.A.",
            "Cliente Ejemplo",
            "PRJ-00001",
        )
        assert "rellenar" in navegador.llamadas
        assert "rellenar_axas_ms3" not in navegador.llamadas
        assert "No existe ninguna oportunidad PRJ-00001: no habrá duplicado" in final["pasos"]
