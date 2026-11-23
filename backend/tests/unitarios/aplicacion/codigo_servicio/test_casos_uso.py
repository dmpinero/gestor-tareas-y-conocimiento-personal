"""Casos de uso del catálogo de códigos de servicio: delegan en el repositorio y
repiten la operación entera si choca con otra simultánea."""

from gestor_tareas.aplicacion.codigo_servicio.casos_uso import (
    CrearCodigoServicio,
    EliminarCodigoServicio,
    ListarCodigosServicio,
    RenombrarCodigoServicio,
)
from gestor_tareas.dominio.codigo_servicio.entidades import CodigoServicio
from gestor_tareas.dominio.excepciones import ConflictoDeConcurrenciaError


class _RepositorioEnMemoria:
    def __init__(self, conflictos: int = 0) -> None:
        self.codigos: dict[int, CodigoServicio] = {}
        self.llamadas: list[str] = []
        self._conflictos = conflictos
        self._siguiente = 1

    def _quizas_conflicto(self, operacion: str) -> None:
        self.llamadas.append(operacion)
        if self._conflictos:
            self._conflictos -= 1
            raise ConflictoDeConcurrenciaError()

    def listar(self) -> list[CodigoServicio]:
        return sorted(self.codigos.values(), key=lambda c: c.nombre.casefold())

    def crear(self, nombre: str) -> CodigoServicio:
        self._quizas_conflicto("crear")
        codigo = CodigoServicio(id=self._siguiente, nombre=nombre)
        self._siguiente += 1
        self.codigos[codigo.id] = codigo
        return codigo

    def renombrar(self, id_codigo: int, nombre: str) -> CodigoServicio:
        self._quizas_conflicto("renombrar")
        self.codigos[id_codigo] = CodigoServicio(id=id_codigo, nombre=nombre)
        return self.codigos[id_codigo]

    def eliminar(self, id_codigo: int) -> None:
        self._quizas_conflicto("eliminar")
        del self.codigos[id_codigo]


def test_crear_listar_renombrar_y_eliminar() -> None:
    repositorio = _RepositorioEnMemoria()

    creado = CrearCodigoServicio(repositorio).ejecutar("AXAS0025")
    CrearCodigoServicio(repositorio).ejecutar("axas0024")
    assert creado == CodigoServicio(id=1, nombre="AXAS0025")
    assert [c.nombre for c in ListarCodigosServicio(repositorio).ejecutar()] == [
        "axas0024",
        "AXAS0025",
    ]

    renombrado = RenombrarCodigoServicio(repositorio).ejecutar(1, "AXAS0026")
    assert renombrado == CodigoServicio(id=1, nombre="AXAS0026")

    EliminarCodigoServicio(repositorio).ejecutar(2)
    assert ListarCodigosServicio(repositorio).ejecutar() == [renombrado]


def test_las_operaciones_de_gestion_se_reintentan_si_hay_conflicto() -> None:
    repositorio = _RepositorioEnMemoria(conflictos=1)
    assert CrearCodigoServicio(repositorio).ejecutar("AXAS0024").nombre == "AXAS0024"

    repositorio._conflictos = 1
    RenombrarCodigoServicio(repositorio).ejecutar(1, "AXAS0025")
    repositorio._conflictos = 1
    EliminarCodigoServicio(repositorio).ejecutar(1)

    assert repositorio.llamadas == ["crear"] * 2 + ["renombrar"] * 2 + ["eliminar"] * 2
    assert repositorio.codigos == {}
