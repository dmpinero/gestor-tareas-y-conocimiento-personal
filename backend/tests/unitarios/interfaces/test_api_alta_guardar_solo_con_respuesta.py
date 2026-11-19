"""Regresión: el alta solo guarda tras un «Guardar» explícito en la página.

Pruebas del verificador independiente (T2), con el navegador simulado: tiempos
de espera, respuestas a destiempo o repetidas, recargas, fallos en cada paso,
peticiones simultáneas y cuerpos que no son JSON.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from tests.unitarios.interfaces.alta_oportunidades_dobles import (
    CAPTURA_PNG,
    RUTA,
    SOLICITUD,
    enviar_respuesta,
    esperar,
    esperar_fin,
    esperar_pregunta,
    montar_cliente,
)


def test_si_se_agota_la_espera_de_la_pregunta_final_no_se_guarda() -> None:
    cliente, navegadores, _ = montar_cliente(espera_respuesta_segundos=0.3)
    with cliente:
        assert cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code == 201
        estado = esperar_pregunta(cliente, "guardar")

        final = esperar_fin(cliente)

        assert final["estado"] == "error"
        assert "no se ha guardado nada" in final["mensaje_final"]
        # Una respuesta tardía a la pregunta caducada se rechaza.
        assert enviar_respuesta(cliente, estado["pregunta"]["id"], "guardar").status_code == 409
        time.sleep(0.1)
        assert "guardar" not in navegadores[0].llamadas
        assert cliente.get(f"{RUTA}/ejecucion/captura").status_code == 404


def test_si_se_agota_la_espera_del_duplicado_no_se_rellena_ni_se_guarda() -> None:
    cliente, navegadores, _ = montar_cliente(espera_respuesta_segundos=0.3, existe=True)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        esperar_pregunta(cliente, "duplicado")

        assert esperar_fin(cliente)["estado"] == "error"
        assert "rellenar" not in navegadores[0].llamadas
        assert "guardar" not in navegadores[0].llamadas


def test_tras_no_guardar_repetir_la_respuesta_con_guardar_se_rechaza() -> None:
    cliente, navegadores, _ = montar_cliente()
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "guardar")
        id_pregunta = estado["pregunta"]["id"]
        assert enviar_respuesta(cliente, id_pregunta, "no_guardar").status_code == 200
        assert esperar_fin(cliente)["estado"] == "no_guardada"

        assert enviar_respuesta(cliente, id_pregunta, "guardar").status_code == 409
        time.sleep(0.1)
        assert "guardar" not in navegadores[0].llamadas
        assert navegadores[0].llamadas[-1] == "cerrar"


def test_guardar_no_es_una_respuesta_valida_al_duplicado() -> None:
    cliente, navegadores, _ = montar_cliente(existe=True)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "duplicado")
        id_pregunta = estado["pregunta"]["id"]

        assert enviar_respuesta(cliente, id_pregunta, "guardar").status_code == 422
        assert cliente.get(f"{RUTA}/ejecucion").json()["pregunta"]["id"] == id_pregunta
        assert enviar_respuesta(cliente, id_pregunta, "no").status_code == 200

        assert esperar_fin(cliente)["estado"] == "no_guardada"
        assert "rellenar" not in navegadores[0].llamadas
        assert "guardar" not in navegadores[0].llamadas


def test_crear_otra_tras_el_duplicado_no_guarda_por_si_sola() -> None:
    cliente, navegadores, _ = montar_cliente(existe=True)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        duplicado = esperar_pregunta(cliente, "duplicado")
        enviar_respuesta(cliente, duplicado["pregunta"]["id"], "si")

        final = esperar_pregunta(cliente, "guardar")
        assert final["pregunta"]["id"] != duplicado["pregunta"]["id"]
        assert "guardar" not in navegadores[0].llamadas
        enviar_respuesta(cliente, final["pregunta"]["id"], "no_guardar")
        esperar_fin(cliente)
        assert "guardar" not in navegadores[0].llamadas


def test_una_respuesta_con_otro_id_o_valor_no_cambia_nada() -> None:
    cliente, navegadores, _ = montar_cliente()
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "guardar")
        id_pregunta = estado["pregunta"]["id"]

        for otro in (id_pregunta - 1, id_pregunta + 1, 0, -1, 999999):
            respuesta = enviar_respuesta(cliente, otro, "guardar")
            assert respuesta.status_code == 409, (otro, respuesta.text)
            assert respuesta.json()["detalle"]
        assert cliente.get(f"{RUTA}/ejecucion").json() == estado
        for valor in ("GUARDAR", "continuar"):
            assert enviar_respuesta(cliente, id_pregunta, valor).status_code == 422
        assert cliente.get(f"{RUTA}/ejecucion").json() == estado
        assert "guardar" not in navegadores[0].llamadas

        enviar_respuesta(cliente, id_pregunta, "no_guardar")
        esperar_fin(cliente)
        assert "guardar" not in navegadores[0].llamadas


def test_la_respuesta_a_la_intervencion_no_sirve_para_la_pregunta_final() -> None:
    cliente, navegadores, _ = montar_cliente(pedir_intervencion=True)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        intervencion = esperar_pregunta(cliente, "intervencion_manual")
        id_intervencion = intervencion["pregunta"]["id"]
        assert enviar_respuesta(cliente, id_intervencion, "guardar").status_code == 422
        assert enviar_respuesta(cliente, id_intervencion, "continuar").status_code == 200

        final = esperar_pregunta(cliente, "guardar")
        assert enviar_respuesta(cliente, id_intervencion, "continuar").status_code == 409
        time.sleep(0.1)
        assert cliente.get(f"{RUTA}/ejecucion").json()["pregunta"]["id"] == final["pregunta"]["id"]
        assert "guardar" not in navegadores[0].llamadas

        enviar_respuesta(cliente, final["pregunta"]["id"], "guardar")
        resultado = esperar_fin(cliente)
        assert resultado["estado"] == "guardada"
        assert resultado["hay_captura"] is True
        assert navegadores[0].llamadas.count("guardar") == 1
        assert cliente.get(f"{RUTA}/ejecucion/captura").content == CAPTURA_PNG


def test_recargar_la_pagina_o_relanzar_con_la_pregunta_pendiente_no_guarda() -> None:
    cliente, navegadores, _ = montar_cliente()
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "guardar")

        for _ in range(5):  # una recarga de la página solo consulta el estado
            assert cliente.get(f"{RUTA}/ejecucion").json() == estado
            assert cliente.get(f"{RUTA}/configuracion").status_code == 200
        assert cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code == 409

        assert cliente.get(f"{RUTA}/ejecucion").json() == estado
        assert "guardar" not in navegadores[0].llamadas
        assert len(navegadores) == 1
        enviar_respuesta(cliente, estado["pregunta"]["id"], "no_guardar")
        esperar_fin(cliente)


@pytest.mark.parametrize(
    "paso",
    [
        "abrir",
        "buscar_descripcion",
        "iniciar_sesion",
        "cambiar_perfil",
        "existe_oportunidad",
        "rellenar",
        "resumen_formulario",
    ],
)
def test_un_fallo_en_cualquier_paso_termina_en_error_sin_guardar(paso: str) -> None:
    cliente, navegadores, _ = montar_cliente(fallo_en=paso)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json={**SOLICITUD, "descripcion": None})

        final = esperar_fin(cliente)

        assert final["estado"] == "error"
        assert f"Fallo simulado en {paso}" in final["mensaje_final"]
        assert "guardar" not in navegadores[0].llamadas
        assert navegadores[0].llamadas[-1] == "cerrar"


def _lanzar_dos_a_la_vez(cliente: TestClient) -> list[int]:
    barrera = threading.Barrier(2)

    def lanzar() -> int:
        barrera.wait()
        return cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code

    with ThreadPoolExecutor(2) as hilos:
        return sorted(f.result() for f in [hilos.submit(lanzar) for _ in range(2)])


def test_dos_lanzamientos_a_la_vez_dan_un_201_y_un_409() -> None:
    for _ in range(20):
        liberar = threading.Event()
        cliente, navegadores, _ = montar_cliente(bloquear_abrir=liberar)
        with cliente:
            assert _lanzar_dos_a_la_vez(cliente) == [201, 409]
            liberar.set()
            estado = esperar_pregunta(cliente, "guardar")
            enviar_respuesta(cliente, estado["pregunta"]["id"], "no_guardar")
            esperar_fin(cliente)
            assert len(navegadores) == 1
            assert "guardar" not in navegadores[0].llamadas


def test_dos_guardar_a_la_vez_guardan_una_sola_vez() -> None:
    cliente, navegadores, _ = montar_cliente()
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        id_pregunta = esperar_pregunta(cliente, "guardar")["pregunta"]["id"]
        barrera = threading.Barrier(2)

        def guardar() -> int:
            barrera.wait()
            return enviar_respuesta(cliente, id_pregunta, "guardar").status_code

        with ThreadPoolExecutor(2) as hilos:
            codigos = sorted(f.result() for f in [hilos.submit(guardar) for _ in range(2)])

        assert codigos == [200, 409]
        esperar_fin(cliente)
        assert navegadores[0].llamadas.count("guardar") == 1


@pytest.mark.parametrize(
    "tipo",
    ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"],
)
def test_una_respuesta_que_no_es_json_se_rechaza_y_no_guarda(tipo: str) -> None:
    """Una petición «simple» de otro origen (sin preflight CORS) no puede guardar."""
    cliente, navegadores, _ = montar_cliente()
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        id_pregunta = esperar_pregunta(cliente, "guardar")["pregunta"]["id"]
        cuerpo = f'{{"id_pregunta": {id_pregunta}, "valor": "guardar"}}'

        respuesta = cliente.post(
            f"{RUTA}/ejecucion/respuesta",
            content=cuerpo,
            headers={"content-type": tipo, "origin": "https://otro-origen.invalid"},
        )
        lanzamiento = cliente.post(
            f"{RUTA}/ejecucion",
            content='{"prj":"PRJ-00002","duracion":1,"importe":1,"coste":1}',
            headers={"content-type": tipo},
        )

        assert respuesta.status_code == 422
        assert lanzamiento.status_code == 422
        time.sleep(0.1)
        assert cliente.get(f"{RUTA}/ejecucion").json()["pregunta"]["id"] == id_pregunta
        assert "guardar" not in navegadores[0].llamadas
        enviar_respuesta(cliente, id_pregunta, "no_guardar")
        esperar_fin(cliente)


def test_el_alta_no_termina_hasta_que_el_navegador_se_ha_cerrado() -> None:
    """Relanzar justo al terminar no puede abrir otro Chromium sobre el mismo perfil
    mientras el anterior aún se está cerrando."""
    liberar_cierre = threading.Event()
    cliente, navegadores, _ = montar_cliente(bloquear_cerrar=liberar_cierre)
    with cliente:
        cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)
        estado = esperar_pregunta(cliente, "guardar")
        enviar_respuesta(cliente, estado["pregunta"]["id"], "no_guardar")
        esperar(cliente, lambda e: "cerrar" in navegadores[0].llamadas)

        cerrando = cliente.get(f"{RUTA}/ejecucion").json()
        relanzada = cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD)

        assert cerrando["terminada"] is False
        assert cerrando["pregunta"] is None
        assert "Cerrando el navegador" in cerrando["pasos"]
        assert relanzada.status_code == 409
        assert len(navegadores) == 1

        liberar_cierre.set()
        final = esperar_fin(cliente)
        assert final["estado"] == "no_guardada"
        assert navegadores[0].cerrado is True
        assert cliente.post(f"{RUTA}/ejecucion", json=SOLICITUD).status_code == 201
        nueva = esperar_pregunta(cliente, "guardar")
        enviar_respuesta(cliente, nueva["pregunta"]["id"], "no_guardar")
        esperar_fin(cliente)
