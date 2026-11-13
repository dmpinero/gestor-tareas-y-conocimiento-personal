from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.comentario_paso.casos_uso import (
    AnadirComentarioPaso,
    EditarComentarioPaso,
    EliminarComentarioPaso,
    ListarComentariosPaso,
)
from gestor_tareas.dominio.comentario.entidades import ComentarioPaso
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from tests.unitarios.aplicacion.dobles import (
    RepositorioComentariosPasoFalso,
    RepositorioWorkflowsFalso,
)

# 18:30:05.123456 en UTC+2: la aplicación lo guarda como 16:30:05 en UTC.
_AHORA = datetime(2026, 11, 10, 18, 30, 5, 123456, tzinfo=timezone(timedelta(hours=2)))
_AHORA_UTC = datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)


class _Entorno:
    def __init__(self) -> None:
        self.workflows = RepositorioWorkflowsFalso(
            Ventas=["Contacto", "Cierre"], Compras=["Pedido"]
        )
        self.comentarios = RepositorioComentariosPasoFalso(self.workflows)

    def ids(self, workflow: str, paso: str) -> tuple[int, int]:
        return self.workflows.id_de(workflow), self.workflows.paso(workflow, paso).id

    def anadir(self, workflow: str, paso: str, texto: str) -> ComentarioPaso:
        return AnadirComentarioPaso(self.comentarios, reloj=lambda: _AHORA).ejecutar(
            *self.ids(workflow, paso), texto
        )


@pytest.fixture
def entorno() -> _Entorno:
    return _Entorno()


def test_anadir_guarda_el_comentario_con_el_instante_en_utc_sin_fraccion(entorno) -> None:
    comentario = entorno.anadir("Ventas", "Contacto", "Llamar antes de las 10")

    id_workflow, id_paso = entorno.ids("Ventas", "Contacto")
    assert comentario == ComentarioPaso(
        id=1,
        id_workflow=id_workflow,
        id_paso=id_paso,
        texto="Llamar antes de las 10",
        creado=_AHORA_UTC,
    )
    assert entorno.comentarios.comentarios == [comentario]


def test_anadir_usa_el_reloj_real_por_defecto(entorno) -> None:
    antes = datetime.now(UTC).replace(microsecond=0)
    comentario = AnadirComentarioPaso(entorno.comentarios).ejecutar(
        *entorno.ids("Ventas", "Contacto"), "x"
    )

    assert antes <= comentario.creado <= datetime.now(UTC)
    assert comentario.creado.microsecond == 0


def test_listar_devuelve_solo_los_del_paso_en_orden(entorno) -> None:
    entorno.anadir("Ventas", "Contacto", "Uno")
    entorno.anadir("Ventas", "Cierre", "Otro paso")
    entorno.anadir("Ventas", "Contacto", "Dos")

    comentarios = ListarComentariosPaso(entorno.comentarios).ejecutar(
        *entorno.ids("Ventas", "Contacto")
    )

    assert [c.texto for c in comentarios] == ["Uno", "Dos"]


def test_editar_cambia_el_texto_y_pone_editado_sin_tocar_creado(entorno) -> None:
    original = entorno.anadir("Ventas", "Contacto", "Uno")
    despues = _AHORA + timedelta(hours=1)

    editado = EditarComentarioPaso(entorno.comentarios, reloj=lambda: despues).ejecutar(
        *entorno.ids("Ventas", "Contacto"), original.id, "Uno bis"
    )

    assert (editado.texto, editado.creado) == ("Uno bis", _AHORA_UTC)
    assert editado.editado == _AHORA_UTC + timedelta(hours=1)
    assert entorno.comentarios.comentarios == [editado]


def test_eliminar_borra_el_comentario(entorno) -> None:
    uno = entorno.anadir("Ventas", "Contacto", "Uno")
    dos = entorno.anadir("Ventas", "Contacto", "Dos")

    EliminarComentarioPaso(entorno.comentarios).ejecutar(*entorno.ids("Ventas", "Contacto"), uno.id)

    assert entorno.comentarios.comentarios == [dos]


def _operacion(entorno: _Entorno, nombre: str):
    """La operación con los comentarios de un paso, como función (workflow, paso, comentario)."""
    repositorio = entorno.comentarios
    return {
        "anadir": lambda w, p, c: AnadirComentarioPaso(repositorio).ejecutar(w, p, "x"),
        "listar": lambda w, p, c: ListarComentariosPaso(repositorio).ejecutar(w, p),
        "editar": lambda w, p, c: EditarComentarioPaso(repositorio).ejecutar(w, p, c, "x"),
        "eliminar": lambda w, p, c: EliminarComentarioPaso(repositorio).ejecutar(w, p, c),
    }[nombre]


_OPERACIONES = ["anadir", "listar", "editar", "eliminar"]


@pytest.mark.parametrize("operacion", _OPERACIONES)
def test_las_operaciones_en_un_workflow_que_no_existe_lanzan_no_encontrado(
    entorno, operacion
) -> None:
    comentario = entorno.anadir("Ventas", "Contacto", "Uno")
    _, id_paso = entorno.ids("Ventas", "Contacto")

    with pytest.raises(EntidadNoEncontradaError, match="^No existe el workflow con id 99$"):
        _operacion(entorno, operacion)(99, id_paso, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]


@pytest.mark.parametrize("operacion", _OPERACIONES)
def test_las_operaciones_en_un_paso_de_otro_workflow_lanzan_no_encontrado(
    entorno, operacion
) -> None:
    comentario = entorno.anadir("Compras", "Pedido", "Pedir")
    id_ventas = entorno.workflows.id_de("Ventas")
    _, id_paso = entorno.ids("Compras", "Pedido")
    mensaje = f"^No existe el paso con id {id_paso} en el workflow con id {id_ventas}$"

    with pytest.raises(EntidadNoEncontradaError, match=mensaje):
        _operacion(entorno, operacion)(id_ventas, id_paso, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]


@pytest.mark.parametrize("operacion", ["editar", "eliminar"])
def test_editar_o_eliminar_un_comentario_de_otro_paso_lanza_no_encontrado(
    entorno, operacion
) -> None:
    comentario = entorno.anadir("Ventas", "Cierre", "Firmar")
    id_workflow, id_paso = entorno.ids("Ventas", "Contacto")
    mensaje = f"^No existe el comentario con id {comentario.id} en el paso con id {id_paso}$"

    with pytest.raises(EntidadNoEncontradaError, match=mensaje):
        _operacion(entorno, operacion)(id_workflow, id_paso, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]
