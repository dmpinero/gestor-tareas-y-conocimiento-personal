import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.persona.entidades import Persona
from gestor_tareas.infraestructura.persistencia.modelos import EtiquetaModelo, PersonaModelo
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioEtiquetasSqlAlchemy,
    RepositorioPersonasSqlAlchemy,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones

_CATALOGOS = [
    pytest.param(RepositorioEtiquetasSqlAlchemy, EtiquetaModelo, Etiqueta, id="etiquetas"),
    pytest.param(RepositorioPersonasSqlAlchemy, PersonaModelo, Persona, id="personas"),
]


def _filas(sesion, modelo) -> list[tuple[int, str]]:
    sesion.expire_all()
    return [(f.id, f.nombre) for f in sesion.scalars(select(modelo).order_by(modelo.id))]


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_obtener_o_crear_da_de_alta_los_nombres_nuevos(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    resultado = repositorio(sesion_bd).obtener_o_crear(["Urgente", "Casa"])
    sesion_bd.commit()

    filas = _filas(sesion_bd, modelo)
    # Las altas se hacen en orden alfabético, para que las peticiones simultáneas
    # bloqueen los nombres en el mismo orden; el resultado sigue el orden pedido.
    assert [f[1] for f in filas] == ["Casa", "Urgente"]
    assert resultado == [entidad(id=i, nombre=n) for i, n in reversed(filas)]


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_obtener_o_crear_reutiliza_sin_distinguir_mayusculas_y_conserva_la_grafia(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    [original] = repositorio(sesion_bd).obtener_o_crear(["Urgente"])
    sesion_bd.commit()

    resultado = repositorio(sesion_bd).obtener_o_crear(["URGENTE", "urgente"])
    sesion_bd.commit()

    assert resultado == [original, original]
    assert _filas(sesion_bd, modelo) == [(original.id, "Urgente")]


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_los_nombres_que_solo_difieren_en_tildes_son_distintos(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    # El spec pide unicidad sin distinguir mayúsculas, no tildes: la columna usa
    # utf8mb4_0900_as_ci en lugar de la intercalación por defecto (_ai_ci).
    resultado = repositorio(sesion_bd).obtener_o_crear(["Cafe", "CAFÉ"])
    sesion_bd.commit()

    assert [e.nombre for e in resultado] == ["Cafe", "CAFÉ"]
    assert len(_filas(sesion_bd, modelo)) == 2


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_la_base_de_datos_impide_nombres_repetidos_sin_distinguir_mayusculas(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    sesion_bd.add(modelo(nombre="Urgente"))
    sesion_bd.commit()
    sesion_bd.add(modelo(nombre="uRGENTE"))

    with pytest.raises(IntegrityError):
        sesion_bd.commit()
    sesion_bd.rollback()


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_listar_devuelve_el_catalogo_ordenado_sin_distinguir_mayusculas(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    repositorio(sesion_bd).obtener_o_crear(["urgente", "Casa", "bajo"])
    sesion_bd.commit()

    assert [e.nombre for e in repositorio(sesion_bd).listar()] == ["bajo", "Casa", "urgente"]


@pytest.mark.parametrize(("repositorio", "modelo", "entidad"), _CATALOGOS)
def test_obtener_o_crear_resuelve_la_carrera_con_un_alta_concurrente(
    sesion_bd, repositorio, modelo, entidad
) -> None:
    """Otra petición da de alta el mismo nombre entre la búsqueda y la inserción.

    La sesión A abre su instantánea (REPEATABLE READ) antes de que B confirme el
    alta, así que su búsqueda normal no ve la fila de B, la inserción choca con
    la restricción única y el repositorio debe releerla y reutilizarla.
    """
    repositorio(sesion_bd).listar()  # La sesión A abre su transacción e instantánea.
    otra_sesion = FabricaSesiones()
    try:
        [de_b] = repositorio(otra_sesion).obtener_o_crear(["Urgente"])
        otra_sesion.commit()
    finally:
        otra_sesion.close()

    resultado = repositorio(sesion_bd).obtener_o_crear(["urgente", "Casa"])
    sesion_bd.commit()

    assert resultado[0] == de_b
    assert resultado[1].nombre == "Casa"
    assert [n for _, n in _filas(sesion_bd, modelo)] == ["Urgente", "Casa"]
