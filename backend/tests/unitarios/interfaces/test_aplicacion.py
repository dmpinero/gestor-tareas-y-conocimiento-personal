import json

from fastapi.testclient import TestClient

from gestor_tareas.main import crear_aplicacion

cliente = TestClient(crear_aplicacion())


def test_la_api_expone_salud_tareas_catalogos_workflow_y_grupos_de_estados_bajo_api_v1() -> None:
    rutas = set(cliente.get("/openapi.json").json()["paths"])

    assert rutas == {
        "/api/v1/salud",
        "/api/v1/tareas",
        "/api/v1/tareas/{id_tarea}",
        "/api/v1/tareas/{id_tarea}/completada",
        "/api/v1/tareas/{id_tarea}/estado",
        "/api/v1/tareas/{id_tarea}/subtareas",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}/resuelta",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}/comentarios",
        "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}/comentarios/{id_comentario}",
        "/api/v1/tareas/{id_tarea}/comentarios",
        "/api/v1/tareas/{id_tarea}/comentarios/{id_comentario}",
        "/api/v1/etiquetas",
        "/api/v1/personas",
        "/api/v1/workflow-oportunidades/pasos",
        "/api/v1/workflow-oportunidades/pasos/{id_paso}",
        "/api/v1/workflow-oportunidades/pasos/orden",
        "/api/v1/grupos-estados",
        "/api/v1/grupos-estados/{id_grupo}",
        "/api/v1/grupos-estados/{id_grupo}/estados",
        "/api/v1/grupos-estados/{id_grupo}/estados/{id_estado}",
        "/api/v1/grupos-estados/{id_grupo}/orden",
    }


def test_la_api_publica_los_metodos_de_cada_ruta_nueva_o_cambiada() -> None:
    rutas = cliente.get("/openapi.json").json()["paths"]
    subtarea = "/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}"

    assert set(rutas["/api/v1/tareas/{id_tarea}"]) == {"put", "delete"}
    assert set(rutas[f"{subtarea}/comentarios"]) == {"get", "post"}
    assert set(rutas[f"{subtarea}/comentarios/{{id_comentario}}"]) == {"put", "delete"}
    grupos = "/api/v1/grupos-estados"
    assert set(rutas[grupos]) == {"get", "post"}
    assert set(rutas[f"{grupos}/{{id_grupo}}"]) == {"put", "delete"}
    assert set(rutas[f"{grupos}/{{id_grupo}}/estados"]) == {"post"}
    assert set(rutas[f"{grupos}/{{id_grupo}}/estados/{{id_estado}}"]) == {"put", "delete"}
    assert set(rutas[f"{grupos}/{{id_grupo}}/orden"]) == {"put"}
    assert set(rutas["/api/v1/tareas/{id_tarea}/estado"]) == {"patch"}


def test_la_tarea_publica_su_grupo_de_estados_y_su_estado_como_claves_obligatorias() -> None:
    componentes = cliente.get("/openapi.json").json()["components"]["schemas"]
    salida = componentes["TareaSalidaEsquema"]
    alta = componentes["TareaCrearEsquema"]

    assert {"grupo_estados", "estado"} <= set(salida["required"])
    for campo, componente in (
        ("grupo_estados", "GrupoEstadosDeTareaEsquema"),
        ("estado", "EstadoDeTareaEsquema"),
    ):
        assert salida["properties"][campo]["anyOf"] == [
            {"$ref": f"#/components/schemas/{componente}"},
            {"type": "null"},
        ]
    assert "grupo_estados_id" not in alta.get("required", [])
    assert alta["properties"]["grupo_estados_id"]["anyOf"] == [
        {"type": "integer"},
        {"type": "null"},
    ]
    assert componentes["TareaEstadoEsquema"]["properties"]["estado_id"]["type"] == "integer"


def test_los_comentarios_de_las_subtareas_reutilizan_los_esquemas_de_los_de_la_tarea() -> None:
    esquema = cliente.get("/openapi.json").json()
    rutas = esquema["paths"]
    de_tarea = rutas["/api/v1/tareas/{id_tarea}/comentarios"]
    de_subtarea = rutas["/api/v1/tareas/{id_tarea}/subtareas/{id_subtarea}/comentarios"]

    def esquema_de_exito(operacion: dict, codigo: str) -> dict:
        esquema = operacion["responses"][codigo]["content"]["application/json"]["schema"]
        return esquema.get("items", esquema)

    for metodo, exito in (("get", "200"), ("post", "201")):
        assert de_subtarea[metodo]["responses"].keys() == de_tarea[metodo]["responses"].keys()
        assert esquema_de_exito(de_subtarea[metodo], exito) == {
            "$ref": "#/components/schemas/ComentarioSalidaEsquema"
        }
        assert esquema_de_exito(de_tarea[metodo], exito) == esquema_de_exito(
            de_subtarea[metodo], exito
        )
    assert de_subtarea["post"]["requestBody"] == de_tarea["post"]["requestBody"]
    componentes = esquema["components"]["schemas"]
    assert "PasoOportunidadSalidaEsquema" not in componentes
    assert "PasoHechoEsquema" not in componentes


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
