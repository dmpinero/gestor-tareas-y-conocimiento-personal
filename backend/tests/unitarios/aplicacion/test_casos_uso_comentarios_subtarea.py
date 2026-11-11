from datetime import UTC, datetime, timedelta, timezone

import pytest

from gestor_tareas.aplicacion.comentario_subtarea.anadir_comentario_subtarea import (
    AnadirComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.editar_comentario_subtarea import (
    EditarComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.eliminar_comentario_subtarea import (
    EliminarComentarioSubtarea,
)
from gestor_tareas.aplicacion.comentario_subtarea.listar_comentarios_subtarea import (
    ListarComentariosSubtarea,
)
from gestor_tareas.dominio.comentario.entidades import ComentarioSubtarea
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.tarea.entidades import Subtarea, Tarea
from tests.unitarios.aplicacion.dobles import (
    RepositorioComentariosSubtareaFalso,
    RepositorioTareasFalso,
)

# 18:30:05.123456 en UTC+2: la aplicación lo guarda como 16:30:05 en UTC.
_AHORA = datetime(2026, 11, 10, 18, 30, 5, 123456, tzinfo=timezone(timedelta(hours=2)))
_AHORA_UTC = datetime(2026, 11, 10, 16, 30, 5, tzinfo=UTC)


class _Entorno:
    def __init__(self) -> None:
        self.tareas = RepositorioTareasFalso()
        self.comentarios = RepositorioComentariosSubtareaFalso(self.tareas)
        self.mudanza = self._tarea("Mudanza", "Cajas", "Camión")
        self.viaje = self._tarea("Viaje", "Billetes")

    def _tarea(self, nombre: str, *subtareas: str) -> Tarea:
        return self.tareas.crear(
            Tarea(
                nombre=nombre,
                descripcion="d",
                fecha_creacion=datetime(2026, 11, 10),
                subtareas=[Subtarea(nombre=s) for s in subtareas],
            )
        )

    def anadir(self, tarea: Tarea, indice: int, texto: str) -> ComentarioSubtarea:
        return AnadirComentarioSubtarea(self.comentarios, reloj=lambda: _AHORA).ejecutar(
            tarea.id, tarea.subtareas[indice].id, texto
        )


@pytest.fixture
def entorno() -> _Entorno:
    return _Entorno()


def test_anadir_guarda_el_comentario_con_el_instante_en_utc_sin_fraccion(entorno) -> None:
    comentario = entorno.anadir(entorno.mudanza, 0, "Pedir cajas")

    assert comentario == ComentarioSubtarea(
        id=1,
        id_tarea=entorno.mudanza.id,
        id_subtarea=entorno.mudanza.subtareas[0].id,
        texto="Pedir cajas",
        creado=_AHORA_UTC,
    )
    assert entorno.comentarios.comentarios == [comentario]


def test_anadir_usa_el_reloj_real_por_defecto(entorno) -> None:
    antes = datetime.now(UTC).replace(microsecond=0)
    comentario = AnadirComentarioSubtarea(entorno.comentarios).ejecutar(
        entorno.mudanza.id, entorno.mudanza.subtareas[0].id, "x"
    )

    assert antes <= comentario.creado <= datetime.now(UTC)
    assert comentario.creado.microsecond == 0


def test_listar_devuelve_solo_los_de_la_subtarea_en_orden(entorno) -> None:
    entorno.anadir(entorno.mudanza, 0, "Uno")
    entorno.anadir(entorno.mudanza, 1, "Otra subtarea")
    entorno.anadir(entorno.mudanza, 0, "Dos")

    comentarios = ListarComentariosSubtarea(entorno.comentarios).ejecutar(
        entorno.mudanza.id, entorno.mudanza.subtareas[0].id
    )

    assert [c.texto for c in comentarios] == ["Uno", "Dos"]


def test_editar_cambia_el_texto_y_pone_editado_sin_tocar_creado(entorno) -> None:
    original = entorno.anadir(entorno.mudanza, 0, "Uno")
    despues = _AHORA + timedelta(hours=1)

    editado = EditarComentarioSubtarea(entorno.comentarios, reloj=lambda: despues).ejecutar(
        entorno.mudanza.id, entorno.mudanza.subtareas[0].id, original.id, "Uno bis"
    )

    assert (editado.texto, editado.creado) == ("Uno bis", _AHORA_UTC)
    assert editado.editado == _AHORA_UTC + timedelta(hours=1)
    assert entorno.comentarios.comentarios == [editado]


def test_eliminar_borra_el_comentario(entorno) -> None:
    uno = entorno.anadir(entorno.mudanza, 0, "Uno")
    dos = entorno.anadir(entorno.mudanza, 0, "Dos")

    EliminarComentarioSubtarea(entorno.comentarios).ejecutar(
        entorno.mudanza.id, entorno.mudanza.subtareas[0].id, uno.id
    )

    assert entorno.comentarios.comentarios == [dos]


def _operaciones(entorno: _Entorno):
    """Cada operación con los comentarios de una subtarea, como (nombre, función)."""
    return [
        (
            "anadir",
            lambda t, s, c: AnadirComentarioSubtarea(entorno.comentarios).ejecutar(t, s, "x"),
        ),
        ("listar", lambda t, s, c: ListarComentariosSubtarea(entorno.comentarios).ejecutar(t, s)),
        (
            "editar",
            lambda t, s, c: EditarComentarioSubtarea(entorno.comentarios).ejecutar(t, s, c, "x"),
        ),
        (
            "eliminar",
            lambda t, s, c: EliminarComentarioSubtarea(entorno.comentarios).ejecutar(t, s, c),
        ),
    ]


@pytest.mark.parametrize("operacion", ["anadir", "listar", "editar", "eliminar"])
def test_las_operaciones_en_una_tarea_que_no_existe_lanzan_no_encontrada(
    entorno, operacion
) -> None:
    comentario = entorno.anadir(entorno.mudanza, 0, "Uno")
    funcion = dict(_operaciones(entorno))[operacion]

    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 99$"):
        funcion(99, entorno.mudanza.subtareas[0].id, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]


@pytest.mark.parametrize("operacion", ["anadir", "listar", "editar", "eliminar"])
def test_las_operaciones_en_una_subtarea_de_otra_tarea_lanzan_no_encontrada(
    entorno, operacion
) -> None:
    comentario = entorno.anadir(entorno.viaje, 0, "Comprar")
    funcion = dict(_operaciones(entorno))[operacion]
    id_subtarea = entorno.viaje.subtareas[0].id
    mensaje = (
        f"^No existe la subtarea con id {id_subtarea} en la tarea con id {entorno.mudanza.id}$"
    )

    with pytest.raises(EntidadNoEncontradaError, match=mensaje):
        funcion(entorno.mudanza.id, id_subtarea, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]


@pytest.mark.parametrize("operacion", ["editar", "eliminar"])
def test_editar_o_eliminar_un_comentario_de_otra_subtarea_lanza_no_encontrada(
    entorno, operacion
) -> None:
    comentario = entorno.anadir(entorno.mudanza, 1, "Alquilar")
    funcion = dict(_operaciones(entorno))[operacion]
    id_subtarea = entorno.mudanza.subtareas[0].id
    mensaje = (
        f"^No existe el comentario con id {comentario.id} en la subtarea con id {id_subtarea}$"
    )

    with pytest.raises(EntidadNoEncontradaError, match=mensaje):
        funcion(entorno.mudanza.id, id_subtarea, comentario.id)

    assert entorno.comentarios.comentarios == [comentario]
