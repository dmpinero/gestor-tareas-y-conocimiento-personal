from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.nombres_catalogo import ordenar_nombres
from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    EtiquetaModelo,
    PersonaModelo,
    TareaModelo,
)


def _a_entidad(modelo: TareaModelo) -> Tarea:
    return Tarea(
        id=modelo.id,
        nombre=modelo.nombre,
        prioridad=modelo.prioridad,
        descripcion=modelo.descripcion,
        fecha_creacion=modelo.fecha_creacion,
        fecha_vencimiento=modelo.fecha_vencimiento,
        etiquetas=ordenar_nombres(e.nombre for e in modelo.etiquetas),
        asignados=ordenar_nombres(p.nombre for p in modelo.asignados),
    )


class RepositorioTareasSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _filas_catalogo[M: (EtiquetaModelo, PersonaModelo)](
        self, modelo: type[M], nombres: list[str]
    ) -> list[M]:
        """Filas del catálogo con esos nombres, que ya deben existir."""
        if not nombres:
            return []
        filas = list(self._sesion.scalars(select(modelo).where(modelo.nombre.in_(nombres))))
        if len(filas) != len(nombres):
            raise ValueError(f"Faltan nombres en el catálogo {modelo.__tablename__}: {nombres}")
        return filas

    def _asignar_datos(self, modelo: TareaModelo, tarea: Tarea) -> None:
        modelo.nombre = tarea.nombre
        modelo.prioridad = tarea.prioridad
        modelo.descripcion = tarea.descripcion
        modelo.fecha_creacion = tarea.fecha_creacion
        modelo.fecha_vencimiento = tarea.fecha_vencimiento
        # Asignar la lista completa sustituye el conjunto de enlaces de la tarea.
        modelo.etiquetas = self._filas_catalogo(EtiquetaModelo, tarea.etiquetas)
        modelo.asignados = self._filas_catalogo(PersonaModelo, tarea.asignados)

    def crear(self, tarea: Tarea) -> Tarea:
        modelo = TareaModelo()
        self._asignar_datos(modelo, tarea)
        self._sesion.add(modelo)
        self._sesion.commit()
        return _a_entidad(modelo)

    def listar(self) -> list[Tarea]:
        modelos = self._sesion.scalars(select(TareaModelo).order_by(TareaModelo.id)).all()
        return [_a_entidad(m) for m in modelos]

    def obtener_por_id(self, id_tarea: int) -> Tarea | None:
        modelo = self._sesion.get(TareaModelo, id_tarea)
        return _a_entidad(modelo) if modelo is not None else None

    def actualizar(self, tarea: Tarea) -> Tarea:
        modelo = self._sesion.get(TareaModelo, tarea.id)
        self._asignar_datos(modelo, tarea)
        self._sesion.commit()
        return _a_entidad(modelo)
