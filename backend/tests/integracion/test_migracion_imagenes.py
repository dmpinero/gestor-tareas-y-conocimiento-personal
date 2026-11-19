"""Migración de las imágenes de los comentarios: crea solo la tabla de las imágenes
(con espacio para 5 MB) y se deshace borrándola, sin tocar el resto de los datos."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_REVISION = "f1a6c3e8b2d9"
_ANTERIOR = "e2c7a9f4b1d6"


def _alembic() -> Config:
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _tablas_y_comentarios() -> tuple[set[str], list[tuple], str]:
    sesion = FabricaSesiones()
    try:
        tablas = set(inspect(sesion.connection()).get_table_names())
        comentarios = sesion.execute(text("SELECT id, texto FROM comentarios ORDER BY id")).all()
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return tablas, [tuple(c) for c in comentarios], revision
    finally:
        sesion.close()


def _ejecutar(sql: str, **parametros: object) -> None:
    sesion = FabricaSesiones()
    try:
        sesion.execute(text(sql), parametros)
        sesion.commit()
    finally:
        sesion.close()


def test_la_migracion_crea_la_tabla_de_imagenes_y_se_deshace() -> None:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        tablas, _, revision = _tablas_y_comentarios()
        assert "imagenes" not in tablas
        assert revision == _ANTERIOR
        _ejecutar(
            "INSERT INTO tareas (nombre, descripcion, fecha_creacion, fecha_vencimiento, "
            "completada) VALUES ('T', 'd', '2026-11-10 09:00:00', '2026-12-01 10:00:00', 0)"
        )
        _ejecutar(
            "INSERT INTO comentarios (tarea_id, texto, creado) "
            "SELECT id, '<p>Hola</p>', '2026-11-10 09:00:00' FROM tareas"
        )
        _, comentarios_antes, _ = _tablas_y_comentarios()

        command.upgrade(_alembic(), _REVISION)

        tablas, comentarios, revision = _tablas_y_comentarios()
        assert "imagenes" in tablas
        assert (comentarios, revision) == (comentarios_antes, _REVISION)
        sesion = FabricaSesiones()
        try:
            columnas = {
                c["name"]: str(c["type"]).upper()
                for c in inspect(sesion.connection()).get_columns("imagenes")
            }
            juego = sesion.scalar(
                text(
                    "SELECT TABLE_COLLATION FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'imagenes'"
                )
            )
        finally:
            sesion.close()
        assert set(columnas) == {"id", "tipo", "tamano", "contenido", "creada"}
        assert columnas["contenido"] == "MEDIUMBLOB"
        assert juego.startswith("utf8mb4")
        # Cabe una imagen de 5 MB.
        _ejecutar(
            "INSERT INTO imagenes (id, tipo, tamano, contenido, creada) "
            "VALUES (:i, 'image/png', :t, :c, '2026-11-19 10:00:00')",
            i="a" * 32,
            t=5 * 1024 * 1024,
            c=b"\x00" * (5 * 1024 * 1024),
        )

        command.downgrade(_alembic(), _ANTERIOR)

        tablas, comentarios, revision = _tablas_y_comentarios()
        assert "imagenes" not in tablas
        assert (comentarios, revision) == (comentarios_antes, _ANTERIOR)
    finally:
        command.upgrade(_alembic(), "head")
