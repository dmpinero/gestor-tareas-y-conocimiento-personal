from gestor_tareas.aplicacion.etiqueta.listar_etiquetas import ListarEtiquetas
from gestor_tareas.aplicacion.persona.listar_personas import ListarPersonas
from gestor_tareas.dominio.etiqueta.entidades import Etiqueta
from gestor_tareas.dominio.persona.entidades import Persona
from tests.unitarios.aplicacion.dobles import RepositorioEtiquetasFalso, RepositorioPersonasFalso


def test_listar_etiquetas_las_devuelve_ordenadas_sin_distinguir_mayusculas() -> None:
    repositorio = RepositorioEtiquetasFalso("urgente", "Casa", "bajo")

    assert ListarEtiquetas(repositorio).ejecutar() == [
        Etiqueta(id=3, nombre="bajo"),
        Etiqueta(id=2, nombre="Casa"),
        Etiqueta(id=1, nombre="urgente"),
    ]


def test_listar_personas_las_devuelve_ordenadas_sin_distinguir_mayusculas() -> None:
    repositorio = RepositorioPersonasFalso("Lucía", "ana")

    assert ListarPersonas(repositorio).ejecutar() == [
        Persona(id=2, nombre="ana"),
        Persona(id=1, nombre="Lucía"),
    ]


def test_listar_catalogos_vacios_devuelve_lista_vacia() -> None:
    assert ListarEtiquetas(RepositorioEtiquetasFalso()).ejecutar() == []
    assert ListarPersonas(RepositorioPersonasFalso()).ejecutar() == []
