from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.tarea.entidades import Tarea
from gestor_tareas.infraestructura.persistencia.modelos import TareaModelo


def _a_entidad(modelo: TareaModelo) -> Tarea:
    return Tarea(
        id=modelo.id,
        nombre=modelo.nombre,
        prioridad=modelo.prioridad,
        descripcion=modelo.descripcion,
        fecha_hora=modelo.fecha_hora,
    )


class RepositorioTareasSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def crear(self, tarea: Tarea) -> Tarea:
        modelo = TareaModelo(
            nombre=tarea.nombre,
            prioridad=tarea.prioridad,
            descripcion=tarea.descripcion,
            fecha_hora=tarea.fecha_hora,
        )
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
        modelo.nombre = tarea.nombre
        modelo.prioridad = tarea.prioridad
        modelo.descripcion = tarea.descripcion
        modelo.fecha_hora = tarea.fecha_hora
        self._sesion.commit()
        return _a_entidad(modelo)
