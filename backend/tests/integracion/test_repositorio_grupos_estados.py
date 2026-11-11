from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from gestor_tareas.dominio.excepciones import (
    EntidadConDependenciasError,
    EntidadNoEncontradaError,
    NombreDuplicadoError,
    OrdenDeEstadosInvalidoError,
)
from gestor_tareas.dominio.grupo_estados.entidades import EstadoGrupo, GrupoEstados
from gestor_tareas.dominio.tarea.entidades import ReferenciaEstado, ReferenciaGrupoEstados, Tarea
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_grupos_estados_sqlalchemy import (  # noqa: E501
    RepositorioGruposEstadosSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_tareas_sqlalchemy import (
    RepositorioTareasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones


def _filas(sql: str, **parametros) -> list[tuple]:
    sesion = FabricaSesiones()
    try:
        return [tuple(f) for f in sesion.execute(text(sql), parametros)]
    finally:
        sesion.close()


def _estados_guardados(id_grupo: int) -> list[tuple[int, str]]:
    return _filas(
        "SELECT posicion, nombre FROM estados_grupo WHERE grupo_id = :g ORDER BY posicion",
        g=id_grupo,
    )


def _grupo(sesion_bd, nombre: str, *estados: str) -> GrupoEstados:
    repositorio = RepositorioGruposEstadosSqlAlchemy(sesion_bd)
    grupo = repositorio.crear(nombre)
    for estado in estados:
        grupo = repositorio.anadir_estado(grupo.id, estado)
    return grupo


def _tarea(sesion_bd, grupo: GrupoEstados | None, estado: int = 0) -> Tarea:
    tarea = Tarea(nombre="T", descripcion="d", fecha_creacion=datetime(2026, 11, 11, 9, 0, 0))
    if grupo is not None:
        tarea.grupo_estados = ReferenciaGrupoEstados(id=grupo.id, nombre=grupo.nombre)
        e = grupo.estados[estado]
        tarea.estado = ReferenciaEstado(id=e.id, nombre=e.nombre)
    return RepositorioTareasSqlAlchemy(sesion_bd).crear(tarea)


def _estado_de(id_tarea: int) -> tuple[int | None, int | None]:
    (fila,) = _filas("SELECT grupo_estados_id, estado_id FROM tareas WHERE id = :t", t=id_tarea)
    return fila


def test_un_grupo_nuevo_no_tiene_estados_ni_tareas(sesion_bd) -> None:
    grupo = RepositorioGruposEstadosSqlAlchemy(sesion_bd).crear("Desarrollo")

    assert grupo == GrupoEstados(id=grupo.id, nombre="Desarrollo", estados=[], tareas=0)
    assert _filas("SELECT id, nombre FROM grupos_estados") == [(grupo.id, "Desarrollo")]


def test_los_grupos_se_listan_por_nombre_sin_distinguir_mayusculas(sesion_bd) -> None:
    for nombre in ("ventas", "Desarrollo", "Bugs"):
        _grupo(sesion_bd, nombre)

    nombres = [g.nombre for g in RepositorioGruposEstadosSqlAlchemy(sesion_bd).listar()]

    assert nombres == ["Bugs", "Desarrollo", "ventas"]


@pytest.mark.parametrize("repetido", ["Desarrollo", "DESARROLLO", "desarrollo"])
def test_no_se_crean_dos_grupos_con_el_mismo_nombre(sesion_bd, repetido) -> None:
    original = _grupo(sesion_bd, "Desarrollo")

    with pytest.raises(
        NombreDuplicadoError, match=f"^Ya existe un grupo de estados llamado «{repetido}»$"
    ):
        RepositorioGruposEstadosSqlAlchemy(sesion_bd).crear(repetido)

    assert _filas("SELECT id, nombre FROM grupos_estados") == [(original.id, "Desarrollo")]
    assert not sesion_bd.in_transaction()


def test_un_nombre_con_otra_tilde_es_otro_grupo(sesion_bd) -> None:
    _grupo(sesion_bd, "Revision")
    _grupo(sesion_bd, "Revisión")
    assert len(_filas("SELECT id FROM grupos_estados")) == 2


def test_renombrar_un_grupo_conserva_sus_estados(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "Hecha")

    renombrado = RepositorioGruposEstadosSqlAlchemy(sesion_bd).renombrar(grupo.id, "Equipo")

    assert renombrado == GrupoEstados(id=grupo.id, nombre="Equipo", estados=grupo.estados)
    assert _filas("SELECT nombre FROM grupos_estados") == [("Equipo",)]
    assert _estados_guardados(grupo.id) == [(1, "Pendiente"), (2, "Hecha")]


def test_renombrar_un_grupo_con_el_nombre_de_otro_no_cambia_nada(sesion_bd) -> None:
    _grupo(sesion_bd, "Ventas")
    grupo = _grupo(sesion_bd, "Desarrollo")

    with pytest.raises(NombreDuplicadoError):
        RepositorioGruposEstadosSqlAlchemy(sesion_bd).renombrar(grupo.id, "VENTAS")

    assert sorted(_filas("SELECT nombre FROM grupos_estados")) == [("Desarrollo",), ("Ventas",)]


@pytest.mark.parametrize(
    "operacion",
    [
        lambda r: r.renombrar(999999, "X"),
        lambda r: r.eliminar(999999),
        lambda r: r.anadir_estado(999999, "X"),
        lambda r: r.renombrar_estado(999999, 1, "X"),
        lambda r: r.eliminar_estado(999999, 1, None),
        lambda r: r.reordenar_estados(999999, []),
    ],
)
def test_un_grupo_que_no_existe_lanza_no_encontrado(sesion_bd, operacion) -> None:
    with pytest.raises(
        EntidadNoEncontradaError, match="^No existe el grupo de estados con id 999999$"
    ):
        operacion(RepositorioGruposEstadosSqlAlchemy(sesion_bd))
    assert not sesion_bd.in_transaction()


def test_cada_estado_nuevo_va_al_final(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "En curso", "Hecha")

    assert [(e.posicion, e.nombre, e.tareas) for e in grupo.estados] == [
        (1, "Pendiente", 0),
        (2, "En curso", 0),
        (3, "Hecha", 0),
    ]
    assert _estados_guardados(grupo.id) == [(1, "Pendiente"), (2, "En curso"), (3, "Hecha")]


def test_un_estado_repetido_en_el_grupo_no_se_guarda(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente")
    otro = _grupo(sesion_bd, "Ventas", "PENDIENTE")

    with pytest.raises(
        NombreDuplicadoError,
        match="^Ya existe un estado llamado «pendiente» en el grupo de estados «Desarrollo»$",
    ):
        RepositorioGruposEstadosSqlAlchemy(sesion_bd).anadir_estado(grupo.id, "pendiente")

    assert _estados_guardados(grupo.id) == [(1, "Pendiente")]
    assert _estados_guardados(otro.id) == [(1, "PENDIENTE")]


def test_renombrar_un_estado_conserva_su_posicion(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "Hecha")

    resultado = RepositorioGruposEstadosSqlAlchemy(sesion_bd).renombrar_estado(
        grupo.id, grupo.estados[0].id, "Por hacer"
    )

    assert [(e.posicion, e.nombre) for e in resultado.estados] == [(1, "Por hacer"), (2, "Hecha")]
    assert _estados_guardados(grupo.id) == [(1, "Por hacer"), (2, "Hecha")]


@pytest.mark.parametrize("operacion", ["renombrar", "eliminar"])
def test_un_estado_de_otro_grupo_lanza_no_encontrado(sesion_bd, operacion) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente")
    ajeno = _grupo(sesion_bd, "Ventas", "Nueva").estados[0].id
    repositorio = RepositorioGruposEstadosSqlAlchemy(sesion_bd)

    with pytest.raises(
        EntidadNoEncontradaError,
        match=f"^No existe el estado con id {ajeno} en el grupo de estados con id {grupo.id}$",
    ):
        if operacion == "renombrar":
            repositorio.renombrar_estado(grupo.id, ajeno, "X")
        else:
            repositorio.eliminar_estado(grupo.id, ajeno, None)

    assert _filas("SELECT nombre FROM estados_grupo WHERE id = :e", e=ajeno) == [("Nueva",)]


@pytest.mark.parametrize("posicion", [0, 1, 2, 3])
def test_eliminar_un_estado_renumera_los_siguientes(sesion_bd, posicion) -> None:
    nombres = ["A", "B", "C", "D"]
    grupo = _grupo(sesion_bd, "G", *nombres)

    resultado = RepositorioGruposEstadosSqlAlchemy(sesion_bd).eliminar_estado(
        grupo.id, grupo.estados[posicion].id, None
    )

    quedan = [n for i, n in enumerate(nombres) if i != posicion]
    assert [(e.posicion, e.nombre) for e in resultado.estados] == list(enumerate(quedan, start=1))
    assert _estados_guardados(grupo.id) == list(enumerate(quedan, start=1))


def test_los_grupos_cuentan_sus_tareas_y_las_de_cada_estado(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "Hecha")
    otro = _grupo(sesion_bd, "Ventas", "Nueva")
    _tarea(sesion_bd, grupo)
    _tarea(sesion_bd, grupo)
    _tarea(sesion_bd, grupo, estado=1)
    _tarea(sesion_bd, otro)
    _tarea(sesion_bd, None)

    por_nombre = {g.nombre: g for g in RepositorioGruposEstadosSqlAlchemy(sesion_bd).listar()}

    assert por_nombre["Desarrollo"].tareas == 3
    assert [(e.nombre, e.tareas) for e in por_nombre["Desarrollo"].estados] == [
        ("Pendiente", 2),
        ("Hecha", 1),
    ]
    assert (por_nombre["Ventas"].tareas, por_nombre["Ventas"].estados[0].tareas) == (1, 1)


def test_un_estado_con_tareas_no_se_elimina_sin_destino(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "Hecha")
    tarea = _tarea(sesion_bd, grupo)

    with pytest.raises(EntidadConDependenciasError):
        RepositorioGruposEstadosSqlAlchemy(sesion_bd).eliminar_estado(
            grupo.id, grupo.estados[0].id, None
        )

    assert _estados_guardados(grupo.id) == [(1, "Pendiente"), (2, "Hecha")]
    assert _estado_de(tarea.id) == (grupo.id, grupo.estados[0].id)
    assert not sesion_bd.in_transaction()


def test_eliminar_un_estado_mueve_antes_sus_tareas_al_destino(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente", "En curso", "Hecha")
    pendiente, _, hecha = grupo.estados
    tareas = [_tarea(sesion_bd, grupo), _tarea(sesion_bd, grupo), _tarea(sesion_bd, grupo, 2)]

    resultado = RepositorioGruposEstadosSqlAlchemy(sesion_bd).eliminar_estado(
        grupo.id, pendiente.id, hecha.id
    )

    assert [(e.posicion, e.nombre, e.tareas) for e in resultado.estados] == [
        (1, "En curso", 0),
        (2, "Hecha", 3),
    ]
    assert resultado.tareas == 3
    assert [_estado_de(t.id) for t in tareas] == [(grupo.id, hecha.id)] * 3


def test_eliminar_un_grupo_deja_sus_tareas_sin_grupo_ni_estado(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "Desarrollo", "Pendiente")
    otro = _grupo(sesion_bd, "Ventas", "Nueva")
    suya, ajena = _tarea(sesion_bd, grupo), _tarea(sesion_bd, otro)

    RepositorioGruposEstadosSqlAlchemy(sesion_bd).eliminar(grupo.id)

    assert _filas("SELECT nombre FROM grupos_estados") == [("Ventas",)]
    assert _filas("SELECT nombre FROM estados_grupo") == [("Nueva",)]
    assert _estado_de(suya.id) == (None, None)
    assert _estado_de(ajena.id) == (otro.id, otro.estados[0].id)


def test_reordenar_da_las_posiciones_del_orden_recibido(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "G", "A", "B", "C")
    a, b, c = (e.id for e in grupo.estados)

    resultado = RepositorioGruposEstadosSqlAlchemy(sesion_bd).reordenar_estados(grupo.id, [c, a, b])

    assert [(e.posicion, e.id) for e in resultado.estados] == [(1, c), (2, a), (3, b)]
    assert _estados_guardados(grupo.id) == [(1, "C"), (2, "A"), (3, "B")]


def test_reordenar_con_un_estado_de_otro_grupo_no_cambia_nada(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "G", "A", "B")
    ajeno = _grupo(sesion_bd, "H", "X").estados[0].id

    with pytest.raises(OrdenDeEstadosInvalidoError):
        RepositorioGruposEstadosSqlAlchemy(sesion_bd).reordenar_estados(
            grupo.id, [grupo.estados[1].id, ajeno]
        )

    assert _estados_guardados(grupo.id) == [(1, "A"), (2, "B")]


def test_leer_para_asignar_devuelve_el_grupo_con_sus_estados_sin_confirmar(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "G", "A", "B")
    repositorio = RepositorioGruposEstadosSqlAlchemy(sesion_bd)

    leido = repositorio.leer_para_asignar(grupo.id)

    assert leido == GrupoEstados(
        id=grupo.id,
        nombre="G",
        estados=[EstadoGrupo(id=e.id, nombre=e.nombre, posicion=e.posicion) for e in grupo.estados],
    )
    assert sesion_bd.in_transaction()
    sesion_bd.rollback()
    assert repositorio.leer_para_asignar(999999) is None


# --- El invariante de las tareas lo garantiza también la base de datos -----------


def _ejecutar(sql: str, **parametros) -> None:
    sesion = FabricaSesiones()
    try:
        sesion.execute(text(sql), parametros)
        sesion.commit()
    finally:
        sesion.close()


@pytest.mark.parametrize(
    "valores",
    [
        "grupo_estados_id = :g, estado_id = NULL",
        "grupo_estados_id = NULL, estado_id = :e",
        "grupo_estados_id = :g, estado_id = :ajeno",
    ],
)
def test_la_base_de_datos_rechaza_un_estado_que_no_es_del_grupo_de_la_tarea(
    sesion_bd, valores
) -> None:
    grupo = _grupo(sesion_bd, "G", "A")
    ajeno = _grupo(sesion_bd, "H", "X").estados[0].id
    tarea = _tarea(sesion_bd, grupo)

    with pytest.raises(DBAPIError):
        _ejecutar(
            f"UPDATE tareas SET {valores} WHERE id = :t",  # noqa: S608 - valores fijos del test
            g=grupo.id,
            e=grupo.estados[0].id,
            ajeno=ajeno,
            t=tarea.id,
        )

    assert _estado_de(tarea.id) == (grupo.id, grupo.estados[0].id)


def test_la_base_de_datos_impide_borrar_un_estado_con_tareas(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "G", "A")
    _tarea(sesion_bd, grupo)

    with pytest.raises(DBAPIError):
        _ejecutar("DELETE FROM estados_grupo WHERE id = :e", e=grupo.estados[0].id)
    with pytest.raises(DBAPIError):
        _ejecutar("DELETE FROM grupos_estados WHERE id = :g", g=grupo.id)


def test_obtener_para_modificar_lee_la_tarea_con_su_grupo_y_estado_sin_confirmar(
    sesion_bd,
) -> None:
    grupo = _grupo(sesion_bd, "G", "A", "B")
    creada = _tarea(sesion_bd, grupo, estado=1)
    repositorio = RepositorioTareasSqlAlchemy(sesion_bd)

    tarea = repositorio.obtener_para_modificar(creada.id)

    assert (tarea.grupo_estados, tarea.estado) == (
        ReferenciaGrupoEstados(id=grupo.id, nombre="G"),
        ReferenciaEstado(id=grupo.estados[1].id, nombre="B"),
    )
    assert sesion_bd.in_transaction()
    sesion_bd.rollback()
    assert repositorio.obtener_para_modificar(999999) is None


def test_cambiar_estado_solo_cambia_el_estado(sesion_bd) -> None:
    grupo = _grupo(sesion_bd, "G", "A", "B")
    creada = _tarea(sesion_bd, grupo)
    b = grupo.estados[1]

    tarea = RepositorioTareasSqlAlchemy(sesion_bd).cambiar_estado(
        creada.id, ReferenciaEstado(id=b.id, nombre=b.nombre)
    )

    assert tarea.estado == ReferenciaEstado(id=b.id, nombre="B")
    assert {**vars(tarea), "estado": None} == {**vars(creada), "estado": None}
    assert _estado_de(creada.id) == (grupo.id, b.id)
    with pytest.raises(EntidadNoEncontradaError, match="^No existe la tarea con id 999999$"):
        RepositorioTareasSqlAlchemy(sesion_bd).cambiar_estado(999999, tarea.estado)
