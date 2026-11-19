from datetime import UTC

from sqlalchemy.orm import Session

from gestor_tareas.dominio.imagen.entidades import Imagen
from gestor_tareas.infraestructura.persistencia.modelos import ImagenModelo


class RepositorioImagenesSqlAlchemy:
    """Adaptador de ``RepositorioImagenes`` sobre la tabla ``imagenes``."""

    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, imagen: Imagen) -> None:
        self._sesion.add(
            ImagenModelo(
                id=imagen.id,
                tipo=imagen.tipo,
                tamano=imagen.tamano,
                contenido=imagen.contenido,
                # La columna no guarda la zona: el instante va en UTC.
                creada=imagen.creada.astimezone(UTC).replace(tzinfo=None),
            )
        )
        self._sesion.commit()

    def obtener(self, id_imagen: str) -> Imagen | None:
        fila = self._sesion.get(ImagenModelo, id_imagen)
        if fila is None:
            return None
        return Imagen(
            id=fila.id,
            tipo=fila.tipo,
            contenido=fila.contenido,
            creada=fila.creada.replace(tzinfo=UTC),
        )
