"""API del automatizador de altas de oportunidades, con un navegador simulado."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from gestor_tareas.aplicacion.oportunidad.servicio import ServicioAltaOportunidades
from gestor_tareas.interfaces.api.v1.enrutadores.alta_oportunidades import obtener_servicio
from gestor_tareas.main_automatizador import crear_aplicacion_automatizador
from tests.unitarios.interfaces.alta_oportunidades_dobles import (
    CAPTURA_PNG,
    RUTA,
    SOLICITUD,
    FuenteRota,
    NavegadorSimulado,
    enviar_respuesta,
    esperar_fin,
    esperar_pregunta,
    montar_cliente,
    responder,
)


@dataclass
class Entorno:
    cliente: TestClient
    navegadores: list[NavegadorSimulado]
    preparar: Callable[..., None]


@pytest.fixture
def entorno() -> Iterator[Entorno]:
    # Las opciones de cada navegador se fijan en el test, antes de lanzar el alta.
    opciones: dict[str, object] = {}
    cliente, navegadores, _ = montar_cliente(opciones_navegador=opciones)
    with cliente:
        yield Entorno(cliente, navegadores, lambda **o: opciones.update(o))
        # Libera cualquier ejecución que siga esperando para no dejar hilos colgados.
        for navegador in navegadores:
            navegador.liberar_inicio_sesion.set()
        estado = cliente.get(f"{RUTA}/ejecucion")
        if estado.status_code == 200 and estado.json()["pregunta"]:
            pregunta = estado.json()["pregunta"]
            if pregunta["opciones"]:
                enviar_respuesta(cliente, pregunta["id"], pregunta["opciones"][-1]["valor"])


def test_la_configuracion_muestra_los_valores_fijos_y_las_fechas_calculadas(
    entorno: Entorno,
) -> None:
    respuesta = entorno.cliente.get(f"{RUTA}/configuracion")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["error"] is None
    assert cuerpo["fecha_limite"] == "07/02/2026"
    assert cuerpo["fecha_inicio"] == "28/02/2026"
    valores = cuerpo["valores"]
    assert valores["perfil"] == "Persona Ejemplo"
    assert valores["cliente"] == "[CEJ] Cliente Ejemplo S.A."
    assert valores["dias_fecha_limite"] == 7
    assert valores["comunidades"] == [
        {"nombre": "Comunidad A", "porcentaje": "80"},
        {"nombre": "Comunidad B", "porcentaje": "20"},
    ]
    assert "url_digital_desktop" not in valores


def test_sin_configuracion_el_resumen_explica_el_error(entorno: Entorno) -> None:
    aplicacion = crear_aplicacion_automatizador()
    servicio = ServicioAltaOportunidades(FuenteRota(), lambda c: NavegadorSimulado())
    aplicacion.dependency_overrides[obtener_servicio] = lambda: servicio
    cliente = TestClient(aplicacion)

    cuerpo = cliente.get(f"{RUTA}/configuracion").json()

    assert cuerpo["error"] == "No existe el archivo de configuración /config/x.json."
    assert cuerpo["valores"] is None
    assert cuerpo["fecha_limite"] is None


def test_sin_configuracion_no_se_puede_lanzar_el_alta() -> None:
    navegadores: list[NavegadorSimulado] = []
    aplicacion = crear_aplicacion_automatizador()
    servicio = ServicioAltaOportunidades(
        FuenteRota(), lambda c: navegadores.append(NavegadorSimulado()) or navegadores[-1]
    )
    aplicacion.dependency_overrides[obtener_servicio] = lambda: servicio
    cliente = TestClient(aplicacion)

    respuesta = cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    assert respuesta.status_code == 503
    assert respuesta.json()["detalle"] == (
        "No se puede lanzar el alta: No existe el archivo de configuración /config/x.json."
    )
    assert navegadores == []
    assert cliente.get(f"{RUTA}/ejecucion").status_code == 404


def test_un_codigo_prj_invalido_se_rechaza_con_el_mensaje_del_script(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(f"{RUTA}/ejecucion", json={**SOLICITUD, "prj": "PRJ-12"})

    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == "El código debe tener el formato PRJ-XXXXX (5 dígitos)."
    assert entorno.navegadores == []


def test_falta_la_duracion_se_rechaza(entorno: Entorno) -> None:
    respuesta = entorno.cliente.post(f"{RUTA}/ejecucion", json={**SOLICITUD, "duracion": None})

    assert respuesta.status_code == 422
    assert respuesta.json()["detalle"] == "La duración es obligatoria."


def test_sin_ejecuciones_el_estado_responde_404(entorno: Entorno) -> None:
    assert entorno.cliente.get(f"{RUTA}/ejecucion").status_code == 404
    assert entorno.cliente.get(f"{RUTA}/ejecucion/captura").status_code == 404


def test_guardar_pulsa_guardar_y_deja_la_captura_del_resultado(entorno: Entorno) -> None:
    lanzada = entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
    assert lanzada.status_code == 201
    assert lanzada.json()["prj"] == "PRJ-00001"

    estado = esperar_pregunta(entorno.cliente, "guardar")
    assert estado["pregunta"]["detalle"] == "Nombre: PRJ-00001 Descripción desde las notas"
    assert estado["pregunta"]["opciones"] == [
        {"valor": "guardar", "etiqueta": "Guardar"},
        {"valor": "no_guardar", "etiqueta": "No guardar"},
    ]
    assert "guardar" not in entorno.navegadores[0].llamadas
    responder(entorno.cliente, estado, "guardar")

    final = esperar_fin(entorno.cliente)
    navegador = entorno.navegadores[0]
    assert final["estado"] == "guardada"
    assert final["hay_captura"] is True
    assert final["pregunta"] is None
    assert "guardar" in navegador.llamadas
    assert navegador.cerrado is True
    assert navegador.datos is not None
    assert navegador.datos.nombre == "PRJ-00001 Descripción desde las notas"
    assert navegador.datos.fecha_limite == "07/02/2026"
    assert navegador.datos.fecha_inicio == "28/02/2026"
    assert "Sesión iniciada" in final["pasos"]
    assert "No existe ninguna oportunidad PRJ-00001: no habrá duplicado" in final["pasos"]
    captura = entorno.cliente.get(f"{RUTA}/ejecucion/captura")
    assert captura.status_code == 200
    assert captura.headers["content-type"] == "image/png"
    assert captura.content == CAPTURA_PNG


def test_con_descripcion_no_se_busca_en_las_notas(entorno: Entorno) -> None:
    entorno.cliente.post(f"{RUTA}/ejecucion", json={**SOLICITUD, "descripcion": "Mi proyecto"})

    estado = esperar_pregunta(entorno.cliente, "guardar")
    responder(entorno.cliente, estado, "no_guardar")
    esperar_fin(entorno.cliente)

    navegador = entorno.navegadores[0]
    assert not any(llamada.startswith("buscar_descripcion") for llamada in navegador.llamadas)
    assert navegador.datos is not None
    assert navegador.datos.nombre == "PRJ-00001 Mi proyecto"


def test_no_guardar_termina_sin_guardar_nada(entorno: Entorno) -> None:
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    responder(entorno.cliente, esperar_pregunta(entorno.cliente, "guardar"), "no_guardar")

    final = esperar_fin(entorno.cliente)
    assert final["estado"] == "no_guardada"
    assert final["mensaje_final"] == "No se ha guardado nada."
    assert final["hay_captura"] is False
    assert "guardar" not in entorno.navegadores[0].llamadas
    assert entorno.navegadores[0].cerrado is True
    assert entorno.cliente.get(f"{RUTA}/ejecucion/captura").status_code == 404


def test_si_ya_existe_y_se_responde_no_se_para_sin_crear_nada(entorno: Entorno) -> None:
    entorno.preparar(existe=True)
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    estado = esperar_pregunta(entorno.cliente, "duplicado")
    assert estado["pregunta"]["mensaje"] == (
        "Ya existe una oportunidad con PRJ-00001. ¿Crear otra igualmente?"
    )
    assert [o["valor"] for o in estado["pregunta"]["opciones"]] == ["si", "no"]
    responder(entorno.cliente, estado, "no")

    final = esperar_fin(entorno.cliente)
    navegador = entorno.navegadores[0]
    assert final["estado"] == "no_guardada"
    assert final["mensaje_final"] == "No se ha creado ninguna oportunidad."
    assert "rellenar" not in navegador.llamadas
    assert "guardar" not in navegador.llamadas
    assert navegador.cerrado is True


def test_si_ya_existe_y_se_responde_si_se_sigue_hasta_la_pregunta_final(entorno: Entorno) -> None:
    entorno.preparar(existe=True)
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    responder(entorno.cliente, esperar_pregunta(entorno.cliente, "duplicado"), "si")

    esperar_pregunta(entorno.cliente, "guardar")
    assert "rellenar" in entorno.navegadores[0].llamadas


def test_la_intervencion_manual_espera_a_continuar(entorno: Entorno) -> None:
    entorno.preparar(pedir_intervencion=True)
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    estado = esperar_pregunta(entorno.cliente, "intervencion_manual")
    assert estado["pregunta"]["mensaje"] == (
        "No pude confirmar el cambio de perfil. Cámbialo tú a mano."
    )
    assert estado["pregunta"]["opciones"] == [{"valor": "continuar", "etiqueta": "Continuar"}]
    assert "Perfil activo" not in estado["pasos"]
    responder(entorno.cliente, estado, "continuar")

    estado = esperar_pregunta(entorno.cliente, "guardar")
    assert "Perfil activo" in estado["pasos"]


def test_la_espera_del_inicio_de_sesion_se_muestra_y_no_admite_respuesta(entorno: Entorno) -> None:
    entorno.preparar(esperar_inicio_sesion=True)
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    estado = esperar_pregunta(entorno.cliente, "inicio_sesion")
    assert estado["pregunta"]["mensaje"] == "Inicia sesión en la ventana del navegador."
    assert estado["pregunta"]["opciones"] == []
    respuesta = entorno.cliente.post(
        f"{RUTA}/ejecucion/respuesta",
        json={"id_pregunta": estado["pregunta"]["id"], "valor": "continuar"},
    )
    assert respuesta.status_code == 409

    entorno.navegadores[0].liberar_inicio_sesion.set()
    esperar_pregunta(entorno.cliente, "guardar")


def test_solo_puede_haber_un_alta_a_la_vez(entorno: Entorno) -> None:
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
    esperar_pregunta(entorno.cliente, "guardar")

    respuesta = entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    assert respuesta.status_code == 409
    assert respuesta.json()["detalle"] == (
        "Ya hay un alta de oportunidad en curso; espera a que termine."
    )
    assert len(entorno.navegadores) == 1


def test_al_terminar_un_alta_se_puede_lanzar_otra(entorno: Entorno) -> None:
    primera = entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).json()
    responder(entorno.cliente, esperar_pregunta(entorno.cliente, "guardar"), "no_guardar")
    esperar_fin(entorno.cliente)

    respuesta = entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    assert respuesta.status_code == 201
    assert respuesta.json()["id"] != primera["id"]
    assert respuesta.json()["estado"] == "en_curso"
    assert len(entorno.navegadores) == 2


def test_un_error_de_la_automatizacion_termina_con_su_mensaje(entorno: Entorno) -> None:
    entorno.preparar(
        error_al_iniciar_sesion="Digital Desktop responde 'Forbidden': conecta la VPN."
    )
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

    final = esperar_fin(entorno.cliente)

    assert final["estado"] == "error"
    assert final["mensaje_final"] == "Digital Desktop responde 'Forbidden': conecta la VPN."
    assert entorno.navegadores[0].cerrado is True


def test_una_respuesta_a_otra_pregunta_o_fuera_de_las_opciones_se_rechaza(
    entorno: Entorno,
) -> None:
    entorno.cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
    estado = esperar_pregunta(entorno.cliente, "guardar")
    id_pregunta = estado["pregunta"]["id"]

    otra = entorno.cliente.post(
        f"{RUTA}/ejecucion/respuesta", json={"id_pregunta": id_pregunta + 1, "valor": "guardar"}
    )
    invalida = entorno.cliente.post(
        f"{RUTA}/ejecucion/respuesta", json={"id_pregunta": id_pregunta, "valor": "quizas"}
    )

    assert otra.status_code == 409
    assert invalida.status_code == 422
    assert "guardar" not in entorno.navegadores[0].llamadas


def test_la_api_del_automatizador_documenta_sus_rutas_en_openapi() -> None:
    cliente = TestClient(crear_aplicacion_automatizador())

    rutas = set(cliente.get(f"{RUTA}/openapi.json").json()["paths"])

    assert rutas == {
        f"{RUTA}/salud",
        f"{RUTA}/configuracion",
        f"{RUTA}/ejecucion",
        f"{RUTA}/ejecucion/respuesta",
        f"{RUTA}/ejecucion/captura",
        f"{RUTA}/axas-ms3/configuracion",
        f"{RUTA}/axas-ms3/ejecucion",
    }
    assert cliente.get(f"{RUTA}/salud").json() == {"estado": "ok"}
