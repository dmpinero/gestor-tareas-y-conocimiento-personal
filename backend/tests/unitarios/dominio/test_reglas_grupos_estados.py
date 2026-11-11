import pytest

from gestor_tareas.dominio.excepciones import (
    AsignacionDeEstadoInvalidaError,
    EntidadConDependenciasError,
    OrdenDeEstadosInvalidoError,
)
from gestor_tareas.dominio.grupo_estados.entidades import EstadoGrupo, GrupoEstados
from gestor_tareas.dominio.grupo_estados.reglas import (
    comprobar_destino_de_las_tareas,
    comprobar_nuevo_orden,
    estado_al_asignar,
    estado_de_destino,
    grupo_asignable,
)


def _grupo(*estados: str, tareas: dict[str, int] | None = None) -> GrupoEstados:
    tareas = tareas or {}
    return GrupoEstados(
        id=1,
        nombre="Desarrollo",
        estados=[
            EstadoGrupo(id=10 + i, nombre=nombre, posicion=i, tareas=tareas.get(nombre, 0))
            for i, nombre in enumerate(estados, start=1)
        ],
    )


# --- Orden --------------------------------------------------------------------


@pytest.mark.parametrize("orden", [[11, 12, 13], [13, 11, 12], [12, 13, 11]])
def test_un_orden_con_cada_estado_una_vez_es_valido(orden) -> None:
    comprobar_nuevo_orden([11, 12, 13], orden)


def test_sin_estados_el_unico_orden_valido_es_el_vacio() -> None:
    comprobar_nuevo_orden([], [])
    with pytest.raises(OrdenDeEstadosInvalidoError):
        comprobar_nuevo_orden([], [1])


@pytest.mark.parametrize(
    ("orden", "detalle"),
    [
        ([11, 12, 12, 13], "repetidos: 12"),
        ([11, 13], "faltan: 12"),
        ([11, 12, 13, 99], "no son del grupo: 99"),
        ([11, 11, 99], "repetidos: 11; faltan: 12, 13; no son del grupo: 99"),
    ],
)
def test_un_orden_invalido_indica_que_le_pasa(orden, detalle) -> None:
    with pytest.raises(OrdenDeEstadosInvalidoError) as error:
        comprobar_nuevo_orden([11, 12, 13], orden)

    assert str(error.value) == (
        f"El nuevo orden debe incluir cada estado del grupo exactamente una vez ({detalle})"
    )


# --- Destino de las tareas de un estado que se elimina ---------------------------


def test_un_estado_sin_tareas_se_elimina_sin_indicar_destino() -> None:
    grupo = _grupo("Pendiente", "Hecha")
    comprobar_destino_de_las_tareas(grupo, grupo.estados[0], None)


def test_un_estado_con_tareas_exige_destino() -> None:
    grupo = _grupo("Pendiente", "Hecha", tareas={"Pendiente": 2})

    with pytest.raises(EntidadConDependenciasError) as error:
        comprobar_destino_de_las_tareas(grupo, grupo.estados[0], None)

    assert str(error.value) == (
        "El estado «Pendiente» tiene 2 tareas: indica en mover_a a qué otro estado del grupo "
        "moverlas"
    )


@pytest.mark.parametrize("tareas", [0, 3])
def test_el_destino_puede_ser_cualquier_otro_estado_del_grupo(tareas) -> None:
    grupo = _grupo("Pendiente", "En curso", "Hecha", tareas={"En curso": tareas})
    for destino in (11, 13):
        comprobar_destino_de_las_tareas(grupo, grupo.estados[1], destino)


@pytest.mark.parametrize("tareas", [0, 1])
@pytest.mark.parametrize("destino", [12, 99])
def test_el_destino_no_puede_ser_el_mismo_estado_ni_uno_ajeno(tareas, destino) -> None:
    grupo = _grupo("Pendiente", "En curso", tareas={"En curso": tareas})

    with pytest.raises(EntidadConDependenciasError) as error:
        comprobar_destino_de_las_tareas(grupo, grupo.estados[1], destino)

    assert str(error.value) == (
        f"mover_a debe ser otro estado del grupo de estados «Desarrollo»: el estado con id "
        f"{destino} no lo es"
    )


# --- Asignación de un grupo a una tarea ---------------------------------------------


def test_un_grupo_que_no_existe_no_se_asigna() -> None:
    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        grupo_asignable(None, 7)

    assert str(error.value) == "No existe el grupo de estados con id 7"


def test_un_grupo_sin_estados_no_se_asigna() -> None:
    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        grupo_asignable(_grupo(), 1)

    assert str(error.value) == (
        "El grupo de estados «Desarrollo» no tiene estados: añade al menos uno antes de "
        "asignarlo a una tarea"
    )


def test_un_grupo_con_estados_se_asigna() -> None:
    grupo = _grupo("Pendiente")
    assert grupo_asignable(grupo, 1) is grupo


def test_al_asignar_un_grupo_a_una_tarea_sin_grupo_queda_en_el_primer_estado() -> None:
    grupo = _grupo("Pendiente", "Hecha")
    assert estado_al_asignar(grupo, None, None).nombre == "Pendiente"


def test_el_primer_estado_es_el_de_la_posicion_1_aunque_la_lista_no_este_en_orden() -> None:
    grupo = _grupo("Pendiente", "Hecha")
    grupo.estados.reverse()
    assert estado_al_asignar(grupo, None, None).nombre == "Pendiente"


def test_al_mantener_el_grupo_la_tarea_conserva_su_estado() -> None:
    grupo = _grupo("Pendiente", "En curso", "Hecha")
    assert estado_al_asignar(grupo, 1, 12).nombre == "En curso"


def test_al_cambiar_de_grupo_la_tarea_queda_en_el_primer_estado_del_nuevo() -> None:
    grupo = _grupo("Pendiente", "En curso")
    assert estado_al_asignar(grupo, 2, 12).nombre == "Pendiente"


def test_si_su_estado_ya_no_es_del_grupo_la_tarea_queda_en_el_primero() -> None:
    grupo = _grupo("Pendiente", "En curso")
    assert estado_al_asignar(grupo, 1, 99).nombre == "Pendiente"


# --- Cambio de estado ------------------------------------------------------------


@pytest.mark.parametrize("id_estado", [11, 12, 13])
def test_cualquier_estado_del_grupo_es_alcanzable(id_estado) -> None:
    assert estado_de_destino(_grupo("Pendiente", "En curso", "Hecha"), id_estado).id == id_estado


def test_un_estado_que_no_es_del_grupo_no_es_alcanzable() -> None:
    with pytest.raises(AsignacionDeEstadoInvalidaError) as error:
        estado_de_destino(_grupo("Pendiente"), 99)

    assert str(error.value) == (
        "El estado con id 99 no es del grupo de estados «Desarrollo» de la tarea"
    )
