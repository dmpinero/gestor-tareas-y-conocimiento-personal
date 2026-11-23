from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from gestor_tareas.aplicacion.codigo_servicio.casos_uso import (
    CrearCodigoServicio,
    EliminarCodigoServicio,
    ListarCodigosServicio,
    RenombrarCodigoServicio,
)
from gestor_tareas.dominio.codigo_servicio.entidades import CodigoServicio
from gestor_tareas.infraestructura.persistencia.repositorios.repositorios_catalogos_sqlalchemy import (  # noqa: E501
    RepositorioCodigosServicioSqlAlchemy,
)
from gestor_tareas.interfaces.api.dependencias import obtener_sesion
from gestor_tareas.interfaces.api.respuestas_error import (
    RESPUESTA_CONFLICTO,
    RESPUESTA_CUERPO_MALFORMADO,
    RESPUESTA_NO_ENCONTRADO,
)
from gestor_tareas.interfaces.api.v1.esquemas.catalogos import (
    CodigoServicioEsquema,
    CodigoServicioSalidaEsquema,
)

enrutador = APIRouter(prefix="/codigos-servicio", tags=["Códigos de servicio"])


def _a_esquema(codigo: CodigoServicio) -> CodigoServicioSalidaEsquema:
    return CodigoServicioSalidaEsquema(id=codigo.id, nombre=codigo.nombre)


def _repositorio(sesion: Session) -> RepositorioCodigosServicioSqlAlchemy:
    return RepositorioCodigosServicioSqlAlchemy(sesion)


@enrutador.get("", response_model=list[CodigoServicioSalidaEsquema])
def listar(sesion: Session = Depends(obtener_sesion)) -> list[CodigoServicioSalidaEsquema]:
    """Devuelve el catálogo de códigos de servicio ordenado por nombre sin distinguir
    mayúsculas."""
    return [_a_esquema(c) for c in ListarCodigosServicio(_repositorio(sesion)).ejecutar()]


@enrutador.post(
    "",
    response_model=CodigoServicioSalidaEsquema,
    status_code=status.HTTP_201_CREATED,
    responses={**RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def crear(
    datos: CodigoServicioEsquema, sesion: Session = Depends(obtener_sesion)
) -> CodigoServicioSalidaEsquema:
    """Da de alta un código de servicio (p. ej. «AXAS0024»). El nombre se recorta,
    tiene de 2 a 20 caracteres sin espacios (422) y es único sin distinguir
    mayúsculas (409)."""
    return _a_esquema(CrearCodigoServicio(_repositorio(sesion)).ejecutar(datos.nombre))


@enrutador.put(
    "/{id_codigo:int}",
    response_model=CodigoServicioSalidaEsquema,
    responses={**RESPUESTA_NO_ENCONTRADO, **RESPUESTA_CONFLICTO, **RESPUESTA_CUERPO_MALFORMADO},
)
def renombrar(
    id_codigo: int, datos: CodigoServicioEsquema, sesion: Session = Depends(obtener_sesion)
) -> CodigoServicioSalidaEsquema:
    """Cambia el nombre del código de servicio (mismas reglas que en el alta). 404 si
    no existe."""
    codigo = RenombrarCodigoServicio(_repositorio(sesion)).ejecutar(id_codigo, datos.nombre)
    return _a_esquema(codigo)


@enrutador.delete(
    "/{id_codigo:int}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPUESTA_NO_ENCONTRADO},
)
def eliminar(id_codigo: int, sesion: Session = Depends(obtener_sesion)) -> Response:
    """Elimina el código de servicio del catálogo. 404 si no existe."""
    EliminarCodigoServicio(_repositorio(sesion)).ejecutar(id_codigo)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
