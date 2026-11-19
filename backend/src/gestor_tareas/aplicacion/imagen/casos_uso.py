from collections.abc import Callable
from datetime import datetime
from uuid import uuid4

from gestor_tareas.aplicacion.comentario.anadir_comentario import (
    ahora_en_utc,
    instante_de_comentario,
)
from gestor_tareas.dominio.excepciones import EntidadNoEncontradaError
from gestor_tareas.dominio.imagen.entidades import Imagen
from gestor_tareas.dominio.imagen.errores import (
    ImagenDemasiadoGrandeError,
    ImagenNoAdmitidaError,
)
from gestor_tareas.dominio.imagen.reglas import TAMANO_MAXIMO, detectar_tipo
from gestor_tareas.dominio.imagen.repositorio import RepositorioImagenes


def _nuevo_id() -> str:
    return uuid4().hex


class SubirImagen:
    """Guarda una imagen para los comentarios si es de un tipo admitido (por su
    contenido) y no pasa de ``TAMANO_MAXIMO``. ``contenido`` puede traer un byte de
    más que el máximo: basta para saber que el archivo es demasiado grande sin
    leerlo entero."""

    def __init__(
        self,
        repositorio: RepositorioImagenes,
        reloj: Callable[[], datetime] = ahora_en_utc,
        nuevo_id: Callable[[], str] = _nuevo_id,
    ) -> None:
        self._repositorio = repositorio
        self._reloj = reloj
        self._nuevo_id = nuevo_id

    def ejecutar(self, contenido: bytes) -> Imagen:
        if len(contenido) > TAMANO_MAXIMO:
            raise ImagenDemasiadoGrandeError(
                f"La imagen no puede pasar de {TAMANO_MAXIMO // (1024 * 1024)} MB"
            )
        tipo = detectar_tipo(contenido)
        if tipo is None:
            raise ImagenNoAdmitidaError("El archivo no es una imagen PNG, JPEG, GIF o WebP")
        imagen = Imagen(
            id=self._nuevo_id(),
            tipo=tipo,
            contenido=contenido,
            creada=instante_de_comentario(self._reloj),
        )
        self._repositorio.guardar(imagen)
        return imagen


class ObtenerImagen:
    """Devuelve una imagen guardada; ``EntidadNoEncontradaError`` si no existe."""

    def __init__(self, repositorio: RepositorioImagenes) -> None:
        self._repositorio = repositorio

    def ejecutar(self, id_imagen: str) -> Imagen:
        imagen = self._repositorio.obtener(id_imagen)
        if imagen is None:
            raise EntidadNoEncontradaError(f"No existe la imagen con id {id_imagen}")
        return imagen
