from sqlalchemy import select
from sqlalchemy.orm import Session

from gestor_tareas.dominio.nombres_catalogo import ordenar_nombres
from gestor_tareas.dominio.tarea.entidades import Oportunidad, Tarea, TipoTarea
from gestor_tareas.infraestructura.persistencia.modelos import (
    EtiquetaModelo,
    OportunidadModelo,
    PersonaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.repositorios.conflictos import traducir_conflictos
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    filas_obtenidas,
)


def _a_oportunidad(modelo: OportunidadModelo | None) -> Oportunidad | None:
    if modelo is None:
        return None
    return Oportunidad(
        codigo=modelo.codigo, descripcion=modelo.descripcion, observaciones=modelo.observaciones
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
        tipo=TipoTarea(modelo.tipo) if modelo.tipo is not None else None,
        oportunidad=_a_oportunidad(modelo.oportunidad),
        completada=modelo.completada,
    )


class RepositorioTareasSqlAlchemy:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _filas_catalogo[M: (EtiquetaModelo, PersonaModelo)](
        self, modelo: type[M], nombres: list[str]
    ) -> list[M]:
        """Filas del catálogo con esos nombres, que ya deben existir.

        Se usan las filas que ``obtener_o_crear`` ya devolvió en esta sesión. Solo
        los nombres que no pasaron por él se buscan, con una lectura con bloqueo
        (FOR SHARE) para ver también lo confirmado después de la instantánea.
        """
        if not nombres:
            return []
        filas, faltan = filas_obtenidas(self._sesion, modelo, nombres)
        if faltan:
            consulta = select(modelo).where(modelo.nombre.in_(faltan)).with_for_update(read=True)
            filas.extend(self._sesion.scalars(consulta))
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
        modelo.tipo = tarea.tipo.value if tarea.tipo is not None else None
        self._asignar_oportunidad(modelo, tarea.oportunidad)

    @staticmethod
    def _asignar_oportunidad(modelo: TareaModelo, oportunidad: Oportunidad | None) -> None:
        """Sustituye los datos de oportunidad de la tarea.

        La fila existente se modifica en lugar de reemplazarse: con otra fila con
        la misma clave, SQLAlchemy insertaría la nueva antes de borrar la vieja.
        """
        if oportunidad is None:
            modelo.oportunidad = None
            return
        if modelo.oportunidad is None:
            modelo.oportunidad = OportunidadModelo()
        modelo.oportunidad.codigo = oportunidad.codigo
        modelo.oportunidad.descripcion = oportunidad.descripcion
        modelo.oportunidad.observaciones = oportunidad.observaciones

    def crear(self, tarea: Tarea) -> Tarea:
        with traducir_conflictos(self._sesion):
            modelo = TareaModelo(completada=tarea.completada)
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
        with traducir_conflictos(self._sesion):
            modelo = self._sesion.get(TareaModelo, tarea.id)
            self._asignar_datos(modelo, tarea)
            self._sesion.commit()
        return _a_entidad(modelo)

    def cambiar_completada(self, id_tarea: int, completada: bool) -> Tarea | None:
        with traducir_conflictos(self._sesion):
            modelo = self._sesion.get(TareaModelo, id_tarea)
            if modelo is None:
                return None
            modelo.completada = completada
            self._sesion.commit()
        return _a_entidad(modelo)
