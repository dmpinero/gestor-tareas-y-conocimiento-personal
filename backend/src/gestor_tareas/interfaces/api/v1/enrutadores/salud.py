from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from gestor_tareas.interfaces.api.dependencias import obtener_sesion

enrutador = APIRouter(prefix="/salud", tags=["Salud"])


@enrutador.get("", status_code=status.HTTP_200_OK)
def comprobar_salud(sesion: Session = Depends(obtener_sesion)) -> dict[str, str]:
    """Comprueba que la API está viva y que hay conexión con la base de datos."""
    sesion.execute(text("SELECT 1"))
    return {"estado": "ok"}
