"""Migración de los códigos de servicio: crea el catálogo `codigos_servicio` (nombres
de hasta 20 caracteres, únicos sin distinguir mayúsculas) sin cambiar ningún otro
dato, y se deshace borrándolo."""

from datetime import datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from alembic import command
from gestor_tareas.infraestructura.persistencia.modelos import (
    EtiquetaModelo,
    SubestadoModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "d4e8a2c6f1b3"
_ANTERIOR = "c9a2f6e4d8b1"


def _alembic() -> Config:
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _sesion_y_cerrar(funcion):
    sesion = FabricaSesiones()
    try:
        return funcion(sesion)
    finally:
        sesion.close()


def _preparar_datos() -> None:
    def preparar(sesion) -> None:
        vaciar_tablas(sesion)
        sesion.add(
            TareaModelo(
                nombre="Tarea",
                descripcion="d",
                fecha_creacion=datetime(2026, 11, 10, 9),
                prioridad=1,
                etiquetas=[EtiquetaModelo(nombre="Casa")],
                subestado=SubestadoModelo(nombre="Bloqueado"),
            )
        )
        sesion.commit()

    _sesion_y_cerrar(preparar)


def _foto() -> dict:
    def foto(sesion) -> dict:
        return {
            "tablas": set(inspect(sesion.connection()).get_table_names()),
            "tareas": [tuple(f) for f in sesion.execute(text("SELECT * FROM tareas")).all()],
            "subestados": sesion.execute(text("SELECT * FROM subestados")).all(),
            "etiquetas": sesion.execute(text("SELECT * FROM tarea_etiquetas")).all(),
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    return _sesion_y_cerrar(foto)


def _ejecutar(sql: str) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql))
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


def test_la_migracion_crea_el_catalogo_sin_cambiar_los_datos_y_se_deshace() -> None:
    _preparar_datos()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        antes = _foto()
        assert "codigos_servicio" not in antes["tablas"]
        assert len(antes["tareas"]) == 1

        command.upgrade(_alembic(), _REVISION)

        despues = _foto()
        assert despues["tablas"] == antes["tablas"] | {"codigos_servicio"}
        for clave in ("tareas", "subestados", "etiquetas"):
            assert despues[clave] == antes[clave]
        assert despues["revision"] == _REVISION

        def columna(sesion) -> tuple:
            return sesion.execute(
                text(
                    "SELECT COLLATION_NAME, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE "
                    "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = 'codigos_servicio' AND COLUMN_NAME = 'nombre'"
                )
            ).one()

        assert tuple(_sesion_y_cerrar(columna)) == ("utf8mb4_0900_as_ci", 20, "NO")

        # La base de datos impide los nombres repetidos sin distinguir mayúsculas.
        _ejecutar("INSERT INTO codigos_servicio (nombre) VALUES ('AXAS0024')")
        with pytest.raises(IntegrityError):
            _ejecutar("INSERT INTO codigos_servicio (nombre) VALUES ('axas0024')")

        command.downgrade(_alembic(), _ANTERIOR)

        assert _foto() == antes
    finally:
        command.upgrade(_alembic(), "head")
