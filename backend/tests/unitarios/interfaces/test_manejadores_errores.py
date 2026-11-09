from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient

from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.interfaces.api.manejadores_errores import registrar_manejadores_de_errores


def _construir_app_de_pruebas() -> FastAPI:
    aplicacion = FastAPI()
    registrar_manejadores_de_errores(aplicacion)

    @aplicacion.get("/controlado")
    def _controlado() -> None:
        raise EntidadNoEncontradaError("tarea no encontrada")

    @aplicacion.get("/no-controlado")
    def _no_controlado() -> None:
        raise ValueError("boom inesperado")

    # Dos rutas distintas (decoradores separados) en el mismo path, como ya
    # hace cada enrutador real: reproduce el bug de Starlette que solo tiene
    # en cuenta los métodos de la PRIMERA ruta que coincide parcialmente al
    # construir el Allow de un 405.
    @aplicacion.get("/recurso")
    def _recurso_get() -> dict[str, str]:
        return {"ok": "get"}

    @aplicacion.post("/recurso")
    def _recurso_post() -> dict[str, str]:
        return {"ok": "post"}

    # Una ruta literal y otra con parámetro genérico (sin convertidor de
    # tipo) que coinciden ambas con el mismo path real, como pasaría con
    # "/tareas/{id_tarea}" y "/tareas/pendientes": el
    # parámetro, al no llevar ":int" ni similar, también matchea
    # literalmente "especial".
    @aplicacion.get("/items/{item_id}")
    def _items_get(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    @aplicacion.put("/items/{item_id}")
    def _items_put(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    @aplicacion.get("/items/especial")
    def _items_especial_get() -> dict[str, str]:
        return {"ok": "especial"}

    @aplicacion.post("/items/especial")
    def _items_especial_post() -> dict[str, str]:
        return {"ok": "especial"}

    @aplicacion.post("/subir")
    async def _subir(fichero: UploadFile) -> dict[str, str]:
        return {"nombre": fichero.filename or ""}

    return aplicacion


cliente = TestClient(_construir_app_de_pruebas(), raise_server_exceptions=False)


def test_un_error_no_controlado_devuelve_500_con_traza_completa() -> None:
    respuesta = cliente.get("/no-controlado")

    assert respuesta.status_code == 500
    cuerpo = respuesta.json()
    assert cuerpo["detalle"] == "boom inesperado"
    assert "Traceback" in cuerpo["traza"]
    assert "ValueError" in cuerpo["traza"]


def test_un_error_de_dominio_ya_mapeado_no_incluye_traza() -> None:
    respuesta = cliente.get("/controlado")

    assert respuesta.status_code == 404
    cuerpo = respuesta.json()
    assert cuerpo["detalle"] == "tarea no encontrada"
    assert "traza" not in cuerpo


def test_un_405_incluye_en_allow_los_metodos_de_todas_las_rutas_del_mismo_path() -> None:
    respuesta = cliente.delete("/recurso")

    assert respuesta.status_code == 405
    metodos = {m.strip() for m in respuesta.headers["allow"].split(",")}
    assert metodos == {"GET", "POST"}


def test_un_405_en_una_ruta_literal_no_confunde_los_metodos_con_la_ruta_generica_que_tambien_coincide() -> (  # noqa: E501
    None
):
    respuesta = cliente.delete("/items/especial")

    assert respuesta.status_code == 405
    metodos = {m.strip() for m in respuesta.headers["allow"].split(",")}
    assert metodos == {"GET", "POST"}


def test_una_ruta_inexistente_sigue_devolviendo_404_estandar() -> None:
    respuesta = cliente.get("/no-existe")

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Not Found"}


def test_un_multipart_malformado_se_remapea_de_400_a_422() -> None:
    respuesta = cliente.post(
        "/subir",
        headers={"content-type": "multipart/form-data; boundary=limite"},
        content=b"esto no es un cuerpo multipart valido",
    )

    assert respuesta.status_code == 422
    assert "detalle" in respuesta.json()
