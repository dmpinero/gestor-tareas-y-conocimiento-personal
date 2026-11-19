"""Migración de los subestados: crea el catálogo de subestados y la columna opcional
`subestado_id` de las tareas (clave ajena con ON DELETE SET NULL); todas las tareas
que ya existían quedan sin subestado y el resto de los datos no cambia. Se deshace
borrando la columna y el catálogo."""

from datetime import datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.modelos import (
    ComentarioModelo,
    EtiquetaModelo,
    TareaModelo,
)
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "c9a2f6e4d8b1"
_ANTERIOR = "b3e7d1a9c5f2"


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
        casa = EtiquetaModelo(nombre="Casa")
        for numero in range(3):
            tarea = TareaModelo(
                nombre=f"Tarea {numero}",
                descripcion="d",
                fecha_creacion=datetime(2026, 11, 10, 9, numero),
                prioridad=numero + 1,
                etiquetas=[casa],
            )
            sesion.add(tarea)
            sesion.flush()
            sesion.add(
                ComentarioModelo(
                    tarea_id=tarea.id, texto="<p>Hola</p>", creado=datetime(2026, 11, 10, 9)
                )
            )
        sesion.commit()

    _sesion_y_cerrar(preparar)


def _foto() -> dict:
    """Tablas, columnas de `tareas` y todas las filas de las tablas de las tareas."""

    def foto(sesion) -> dict:
        inspector = inspect(sesion.connection())
        return {
            "tablas": set(inspector.get_table_names()),
            "columnas": [c["name"] for c in inspector.get_columns("tareas")],
            "tareas": [
                tuple(f) for f in sesion.execute(text("SELECT * FROM tareas ORDER BY id")).all()
            ],
            "etiquetas": sesion.execute(text("SELECT * FROM tarea_etiquetas ORDER BY 1")).all(),
            "comentarios": sesion.execute(text("SELECT * FROM comentarios ORDER BY id")).all(),
            "revision": sesion.scalar(text("SELECT version_num FROM alembic_version")),
        }

    return _sesion_y_cerrar(foto)


def _ejecutar(sql: str) -> None:
    def ejecutar(sesion) -> None:
        sesion.execute(text(sql))
        sesion.commit()

    _sesion_y_cerrar(ejecutar)


def test_la_migracion_crea_los_subestados_sin_cambiar_las_tareas_y_se_deshace() -> None:
    _preparar_datos()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        antes = _foto()
        assert "subestados" not in antes["tablas"]
        assert "subestado_id" not in antes["columnas"]
        assert len(antes["tareas"]) == 3

        command.upgrade(_alembic(), _REVISION)

        despues = _foto()
        assert "subestados" in despues["tablas"]
        assert despues["columnas"] == [*antes["columnas"], "subestado_id"]
        # Todas las tareas quedan sin subestado y el resto de sus datos no cambia.
        assert despues["tareas"] == [(*fila, None) for fila in antes["tareas"]]
        for clave in ("etiquetas", "comentarios"):
            assert despues[clave] == antes[clave]
        assert despues["revision"] == _REVISION

        def esquema(sesion) -> tuple:
            regla = sesion.scalar(
                text(
                    "SELECT DELETE_RULE FROM information_schema.REFERENTIAL_CONSTRAINTS "
                    "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME = 'tareas' "
                    "AND REFERENCED_TABLE_NAME = 'subestados'"
                )
            )
            intercalacion = sesion.scalar(
                text(
                    "SELECT COLLATION_NAME FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'subestados' "
                    "AND COLUMN_NAME = 'nombre'"
                )
            )
            nulable = next(
                c["nullable"]
                for c in inspect(sesion.connection()).get_columns("tareas")
                if c["name"] == "subestado_id"
            )
            return regla, intercalacion, nulable

        assert _sesion_y_cerrar(esquema) == ("SET NULL", "utf8mb4_0900_as_ci", True)

        # Borrar un subestado deja sus tareas sin subestado (la base de datos).
        _ejecutar("INSERT INTO subestados (nombre) VALUES ('Bloqueado')")
        _ejecutar(
            "UPDATE tareas SET subestado_id = (SELECT id FROM subestados) WHERE nombre = 'Tarea 1'"
        )
        _ejecutar("DELETE FROM subestados")
        assert _foto()["tareas"] == despues["tareas"]

        command.downgrade(_alembic(), _ANTERIOR)

        assert _foto() == antes
    finally:
        command.upgrade(_alembic(), "head")
