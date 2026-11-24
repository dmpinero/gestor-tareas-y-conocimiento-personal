"""Lectura de la configuración local del alta de oportunidades (un JSON fuera de git)."""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from gestor_tareas.aplicacion.oportunidad.puertos import ConfiguracionAltaInvalidaError
from gestor_tareas.dominio.oportunidad.entidades import (
    NOMBRE_MENU_AXAS_MS3_PREDETERMINADO,
    NOMBRE_MENU_PREDETERMINADO,
    Asignacion,
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
)

_TEXTO = Field(min_length=1)


class _AsignacionJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = _TEXTO
    porcentaje: str = Field(pattern=r"^\d{1,3}$")


class _AxasMs3Json(BaseModel):
    """Bloque ``axas_ms3``: valores fijos de la variante AXAS MS3."""

    model_config = ConfigDict(extra="forbid")

    nombre_menu: str = Field(
        default=NOMBRE_MENU_AXAS_MS3_PREDETERMINADO, min_length=1, max_length=60
    )
    perfil: str = _TEXTO
    responsable_busqueda: str | None = Field(default=None, min_length=1)
    cliente_busqueda: str = _TEXTO
    cliente: str = _TEXTO
    grupo: str = _TEXTO
    tipo: str = _TEXTO
    responsable_operaciones: str = _TEXTO
    responsable_tecnico: str = _TEXTO
    responsable_tecnico_busqueda: str | None = Field(default=None, min_length=1)
    segmentacion: str = _TEXTO
    area_ms3: str = _TEXTO
    fase: str = _TEXTO
    probabilidad: str = Field(pattern=r"^\d{1,3}$")
    dias_fecha_limite: int = Field(ge=0)
    tipo_servicio: str = _TEXTO
    lineas_negocio: list[_AsignacionJson] = Field(min_length=1)
    comunidades: list[_AsignacionJson] = Field(min_length=1)

    def a_dominio(self) -> ConfiguracionAxasMs3:
        return ConfiguracionAxasMs3(
            **self.model_dump(exclude={"lineas_negocio", "comunidades"}),
            lineas_negocio=_asignaciones(self.lineas_negocio),
            comunidades=_asignaciones(self.comunidades),
        )


class _ConfiguracionJson(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url_digital_desktop: str = Field(pattern=r"^https?://")
    url_notion: str = Field(pattern=r"^https?://")
    titulo_pagina_notion: str = _TEXTO
    perfil: str = _TEXTO
    cliente_busqueda: str = _TEXTO
    cliente: str = _TEXTO
    grupo: str = _TEXTO
    tipo: str = _TEXTO
    segmentacion: str = _TEXTO
    fase: str = _TEXTO
    probabilidad: str = Field(pattern=r"^\d{1,3}$")
    dias_fecha_limite: int = Field(ge=0)
    tipo_servicio: str = _TEXTO
    lineas_negocio: list[_AsignacionJson] = Field(min_length=1)
    comunidades: list[_AsignacionJson] = Field(min_length=1)
    nombre_menu: str = Field(default=NOMBRE_MENU_PREDETERMINADO, min_length=1, max_length=60)
    # Opcional: sin él solo está disponible el alta ANES.
    axas_ms3: _AxasMs3Json | None = None


def _asignaciones(asignaciones: list[_AsignacionJson]) -> tuple[Asignacion, ...]:
    return tuple(Asignacion(a.nombre, a.porcentaje) for a in asignaciones)


def _describir(error: ValidationError) -> str:
    partes = []
    for detalle in error.errors():
        campo = ".".join(str(parte) for parte in detalle["loc"])
        if detalle["type"] == "missing":
            partes.append(f"falta el campo '{campo}'")
        elif detalle["type"] == "extra_forbidden":
            partes.append(f"el campo '{campo}' no se reconoce")
        else:
            partes.append(f"el campo '{campo}' no es válido ({detalle['msg']})")
    return "; ".join(partes)


class LectorConfiguracionJson:
    """Lee y valida el JSON en cada llamada, para recoger los cambios sin reiniciar."""

    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta

    def cargar(self) -> ConfiguracionAltaOportunidad:
        if not self._ruta.is_file():
            raise ConfiguracionAltaInvalidaError(
                f"No existe el archivo de configuración {self._ruta}. Créalo a partir de "
                "config/alta_oportunidad.ejemplo.json (consulta el README)."
            )
        try:
            datos = json.loads(self._ruta.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ConfiguracionAltaInvalidaError(
                f"No se pudo leer el archivo de configuración {self._ruta}: {error}"
            ) from error
        try:
            leida = _ConfiguracionJson.model_validate(datos)
        except ValidationError as error:
            raise ConfiguracionAltaInvalidaError(
                f"El archivo de configuración {self._ruta} no es válido: {_describir(error)}"
            ) from error
        return ConfiguracionAltaOportunidad(
            **leida.model_dump(exclude={"lineas_negocio", "comunidades", "axas_ms3"}),
            lineas_negocio=_asignaciones(leida.lineas_negocio),
            comunidades=_asignaciones(leida.comunidades),
            axas_ms3=None if leida.axas_ms3 is None else leida.axas_ms3.a_dominio(),
        )
