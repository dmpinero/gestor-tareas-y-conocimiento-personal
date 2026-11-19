"""Imágenes de los comentarios (capturas de pantalla): se suben aparte y el HTML
del comentario las referencia por su URL relativa."""

from fastapi import APIRouter, Depends, File, Header, Path, Response, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.imagen.casos_uso import ObtenerImagen, SubirImagen
from gestor_tareas.dominio.imagen.reglas import TAMANO_MAXIMO
from gestor_tareas.infraestructura.persistencia.repositorios.repositorio_imagenes_sqlalchemy import (  # noqa: E501
    RepositorioImagenesSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import RESPUESTA_NO_ENCONTRADO
from gestor_tareas.interfaces.api.v1.esquemas.imagen import (
    PATRON_ID_IMAGEN,
    ImagenSalidaEsquema,
    url_de_imagen,
)

enrutador = APIRouter(prefix="/imagenes", tags=["Imágenes"])

_TIPOS_ADMITIDOS = ("image/png", "image/jpeg", "image/gif", "image/webp")

# Cabecera que envía el frontend al subir. Un multipart sin cabeceras propias es
# una petición "simple" para CORS: sin exigirla, una página de otro sitio podría
# subir imágenes a la aplicación desde el navegador de quien la usa. Con ella, el
# navegador tiene que pedir permiso antes (preflight) y la API no lo da.
CABECERA_SUBIDA = "X-Requested-With"
VALOR_CABECERA_SUBIDA = "gestor-tareas"

# Las imágenes no cambian nunca (cada subida tiene su id): se pueden cachear sin fin.
_CACHE_INMUTABLE = "public, max-age=31536000, immutable"


@enrutador.post(
    "",
    response_model=ImagenSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Falta la cabecera X-Requested-With: gestor-tareas"},
        413: {"description": "La imagen pasa de 5 MB"},
        422: {"description": "El archivo no es una imagen PNG, JPEG, GIF o WebP, o falta"},
    },
)
def subir(
    archivo: UploadFile = File(  # noqa: B008
        description="La imagen: PNG, JPEG, GIF o WebP de hasta 5 MB."
    ),
    cabecera: str | None = Header(
        default=None,
        alias=CABECERA_SUBIDA,
        description=f"Obligatoria, con el valor `{VALOR_CABECERA_SUBIDA}` (403 si no).",
    ),
    sesion: Session = Depends(obtener_sesion),
) -> ImagenSalidaEsquema | JSONResponse:
    """Guarda una imagen para ponerla en un comentario y devuelve su URL relativa,
    que es la que admite el `src` de un `img` en el HTML del comentario. El tipo se
    reconoce por el contenido (su firma), no por el nombre ni por el tipo declarado:
    PNG, JPEG, GIF o WebP (422 si no). Como mucho 5 MB (413 si pasa). Exige la
    cabecera `X-Requested-With: gestor-tareas` (403 si falta o es otra)."""
    if cabecera != VALOR_CABECERA_SUBIDA:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detalle": "La subida de imágenes solo se admite desde la propia aplicación"},
        )
    # Se lee como mucho un byte más que el máximo: basta para saber si se pasa.
    contenido = archivo.file.read(TAMANO_MAXIMO + 1)
    imagen = SubirImagen(RepositorioImagenesSqlAlchemy(sesion)).ejecutar(contenido)
    return ImagenSalidaEsquema(
        id=imagen.id, url=url_de_imagen(imagen.id), tipo=imagen.tipo, tamano=imagen.tamano
    )


@enrutador.get(
    "/{id_imagen}",
    response_class=Response,
    responses={
        200: {
            "description": "Los bytes de la imagen, con su tipo de medio",
            "content": {
                tipo: {"schema": {"type": "string", "format": "binary"}}
                for tipo in _TIPOS_ADMITIDOS
            },
        },
        **RESPUESTA_NO_ENCONTRADO,
    },
)
def descargar(
    id_imagen: str = Path(pattern=PATRON_ID_IMAGEN, description="Id de la imagen."),
    sesion: Session = Depends(obtener_sesion),
) -> Response:
    """Devuelve la imagen con el tipo de medio detectado al subirla, para mostrarla
    en el navegador (`inline`) y con caché larga (no cambia nunca); 404 si no existe."""
    imagen = ObtenerImagen(RepositorioImagenesSqlAlchemy(sesion)).ejecutar(id_imagen)
    return Response(
        content=imagen.contenido,
        media_type=imagen.tipo,
        headers={
            "Cache-Control": _CACHE_INMUTABLE,
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )
