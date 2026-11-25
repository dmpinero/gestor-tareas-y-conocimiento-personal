"""Migración del contador congelado de las tareas: añade la columna con el instante
de congelación y congela desde ese momento las tareas ya completadas o en DONE; se
deshace quitando solo esa columna."""

from datetime import UTC, datetime
from pathlib import Path

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from gestor_tareas.infraestructura.persistencia.sesion import FabricaSesiones
from tests.integracion.tablas import vaciar_tablas

_RAIZ = Path(__file__).resolve().parents[2]
_ANTERIOR = "c5e1b8f4a2d7"
# La última revisión, a la que llega "head" (la de los subestados, posterior a esta).
_ULTIMA = "b7d3e5f9a1c4"


def _alembic() -> Config:
    # Sin el alembic.ini: su configuración de logs desactivaría los registradores
    # que ya existen en el proceso de los tests. env.py toma la URL de la aplicación.
    configuracion = Config()
    configuracion.set_main_option("script_location", str(_RAIZ / "alembic"))
    return configuracion


def _ejecutar(sql: str, **parametros: object) -> int | None:
    """Ejecuta la sentencia en su propia transacción y devuelve el id insertado."""
    sesion = FabricaSesiones()
    try:
        resultado = sesion.execute(text(sql), parametros)
        sesion.commit()
        return resultado.lastrowid
    finally:
        sesion.close()


def _ahora() -> datetime:
    return datetime.now(UTC).replace(microsecond=0, tzinfo=None)


def _datos_de_partida() -> dict[str, int]:
    """Tareas en cada combinación de completada y estado, por nombre."""
    id_grupo = _ejecutar("INSERT INTO grupos_estados (nombre) VALUES ('Flujo')")
    ids_estados = {
        nombre: _ejecutar(
            "INSERT INTO estados_grupo (grupo_id, nombre, posicion) VALUES (:g, :n, :p)",
            g=id_grupo,
            n=nombre,
            p=posicion,
        )
        for posicion, nombre in enumerate(["TODO", "done"], start=1)
    }
    tareas = {
        # nombre: (completada, estado)
        "pendiente": (False, None),
        "completada": (True, None),
        "en done": (False, "done"),
        "en todo": (False, "TODO"),
        "completada en todo": (True, "TODO"),
        "completada en done": (True, "done"),
    }
    ids = {}
    for nombre, (completada, estado) in tareas.items():
        ids[nombre] = _ejecutar(
            "INSERT INTO tareas (nombre, descripcion, fecha_creacion, fecha_vencimiento, "
            "completada, grupo_estados_id, estado_id) "
            "VALUES (:n, 'd', '2026-11-10 09:00:00', '2026-12-01 10:00:00', :c, :g, :e)",
            n=nombre,
            c=completada,
            g=id_grupo if estado else None,
            e=ids_estados[estado] if estado else None,
        )
    return ids


def _estado() -> tuple[bool, list[tuple], str]:
    """(si existe la columna, el resto de datos de las tareas, la revisión actual)."""
    sesion = FabricaSesiones()
    try:
        columnas = {c["name"] for c in inspect(sesion.connection()).get_columns("tareas")}
        tareas = sesion.execute(
            text(
                "SELECT id, nombre, fecha_vencimiento, completada, grupo_estados_id, "
                "estado_id FROM tareas ORDER BY id"
            )
        ).all()
        revision = sesion.scalar(text("SELECT version_num FROM alembic_version"))
        return "congelada_en" in columnas, [tuple(t) for t in tareas], revision
    finally:
        sesion.close()


def _congeladas() -> dict[str, datetime | None]:
    sesion = FabricaSesiones()
    try:
        filas = sesion.execute(text("SELECT nombre, congelada_en FROM tareas")).all()
        return {fila.nombre: fila.congelada_en for fila in filas}
    finally:
        sesion.close()


def _comprobar_relleno(desde: datetime, hasta: datetime) -> None:
    congeladas = _congeladas()
    for nombre in ("completada", "en done", "completada en todo", "completada en done"):
        valor = congeladas[nombre]
        assert valor is not None, nombre
        # El instante de la migración, en UTC y sin fracción de segundo.
        assert desde <= valor <= hasta, nombre
        assert valor.microsecond == 0
    assert congeladas["pendiente"] is None
    assert congeladas["en todo"] is None


def test_la_migracion_congela_las_tareas_completadas_o_en_done_y_se_deshace() -> None:
    sesion = FabricaSesiones()
    try:
        vaciar_tablas(sesion)
    finally:
        sesion.close()
    command.downgrade(_alembic(), _ANTERIOR)
    try:
        assert _estado()[0] is False
        _datos_de_partida()
        _, tareas, revision = _estado()
        assert revision == _ANTERIOR
        desde = _ahora()
    except BaseException:
        command.upgrade(_alembic(), "head")
        raise

    command.upgrade(_alembic(), "head")

    assert _estado() == (True, tareas, _ULTIMA)
    _comprobar_relleno(desde, _ahora())

    try:
        # Al deshacerla solo se quita la columna.
        command.downgrade(_alembic(), _ANTERIOR)
        assert _estado() == (False, tareas, _ANTERIOR)
        desde = _ahora()
    finally:
        command.upgrade(_alembic(), "head")

    # Al volver a aplicarla, congela de nuevo las mismas tareas desde ese instante.
    assert _estado() == (True, tareas, _ULTIMA)
    _comprobar_relleno(desde, _ahora())
