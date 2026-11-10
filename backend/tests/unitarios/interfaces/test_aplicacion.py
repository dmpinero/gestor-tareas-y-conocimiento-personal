import json

from fastapi.testclient import TestClient

from gestor_tareas.main import crear_aplicacion

cliente = TestClient(crear_aplicacion())


def test_la_api_expone_salud_tareas_subtareas_comentarios_catalogos_y_workflow_bajo_api_v1() -> (
    None
):
    rutas = set(cliente.get("/openapi.json").json()["paths"])

    assert rutas == {
        "/api/v1/salud",
        "/api/v1/tareas",
        "/api/v1/tareas/{id_tarea}",
        "/api/v1/tareas/{id_tarea}/completada",
        "/api/v1/tareas/{id_tarea}/pasos/{id_paso}",
        "/api/v1/tareas/{id_tarea}/subtareas",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}/resuelta",
        "/api/v1/tareas/{id_tarea}/comentarios",
        "/api/v1/etiquetas",
        "/api/v1/personas",
        "/api/v1/workflow-oportunidades/pasos",
        "/api/v1/workflow-oportunidades/pasos/{id_paso}",
        "/api/v1/workflow-oportunidades/pasos/orden",
    }


def test_ninguna_ruta_exige_autenticacion() -> None:
    esquema = cliente.get("/openapi.json").json()

    assert "securitySchemes" not in esquema.get("components", {})
    for operaciones in esquema["paths"].values():
        for operacion in operaciones.values():
            assert "security" not in operacion


def test_las_metricas_de_prometheus_se_exponen_fuera_del_esquema() -> None:
    respuesta = cliente.get("/metricas")

    assert respuesta.status_code == 200
    assert "http_request" in respuesta.text or "python_info" in respuesta.text


def test_el_titulo_de_la_api_corresponde_al_proyecto() -> None:
    assert cliente.get("/openapi.json").json()["info"]["title"] == (
        "Gestor de Tareas y Conocimiento Personal"
    )


def test_el_contrato_no_publica_esquemas_sin_usar() -> None:
    # Regresión: el enum de dominio `TipoTarea` aparecía en `components.schemas`
    # sin que nada lo referenciara, publicando su docstring interno.
    esquema = cliente.get("/openapi.json").json()
    componentes = set(esquema.get("components", {}).get("schemas", {}))
    sin_componentes = {k: v for k, v in esquema.items() if k != "components"}
    texto = json.dumps(sin_componentes) + json.dumps(
        esquema.get("components", {}).get("schemas", {})
    )
    referenciados = {
        nombre for nombre in componentes if f'"#/components/schemas/{nombre}"' in texto
    }

    assert componentes - referenciados == set()
