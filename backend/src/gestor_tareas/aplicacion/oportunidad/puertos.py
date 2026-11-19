"""Puertos del alta de oportunidades: la configuración local y el navegador."""

from collections.abc import Callable
from typing import Protocol

from gestor_tareas.dominio.oportunidad.entidades import (
    ConfiguracionAltaOportunidad,
    DatosFormulario,
)


class ConfiguracionAltaInvalidaError(Exception):
    """La configuración local falta o no es válida; el mensaje explica qué corregir."""


class AutomatizacionFallidaError(Exception):
    """Fallo esperado de la automatización, con un mensaje para mostrar en la página."""


class FuenteConfiguracionAlta(Protocol):
    def cargar(self) -> ConfiguracionAltaOportunidad:
        """Devuelve la configuración o lanza ``ConfiguracionAltaInvalidaError``."""
        ...


class CanalEjecucion(Protocol):
    """Lo que el navegador puede contar o preguntar a la página mientras trabaja."""

    def informar(self, paso: str) -> None: ...

    def mostrar_espera_inicio_sesion(self, mensaje: str) -> None: ...

    def ocultar_espera(self) -> None: ...

    def pedir_intervencion(self, mensaje: str) -> None:
        """Bloquea hasta que el usuario pulse "Continuar" en la página."""
        ...


class NavegadorOportunidades(Protocol):
    """Automatización del navegador. Cada método se llama desde el mismo hilo."""

    def abrir(self) -> None: ...

    def buscar_descripcion(self, prj: str, canal: CanalEjecucion) -> str: ...

    def iniciar_sesion(self, canal: CanalEjecucion) -> None: ...

    def cambiar_perfil(self, canal: CanalEjecucion) -> None: ...

    def existe_oportunidad(self, prj: str) -> bool: ...

    def rellenar(self, datos: DatosFormulario, canal: CanalEjecucion) -> None: ...

    def resumen_formulario(self) -> str: ...

    def guardar(self) -> bytes:
        """Pulsa Guardar y devuelve la captura PNG del resultado."""
        ...

    def cerrar(self) -> None: ...


FabricaNavegador = Callable[[ConfiguracionAltaOportunidad], NavegadorOportunidades]
