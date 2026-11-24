"""Puertos del alta de oportunidades: la configuración local y el navegador."""

from collections.abc import Callable
from typing import Protocol

from gestor_tareas.dominio.oportunidad.entidades import (
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
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

    def cambiar_perfil(self, perfil: str, canal: CanalEjecucion) -> None: ...

    def existe_oportunidad(self, cliente: str, cliente_busqueda: str, texto: str) -> bool:
        """Busca las oportunidades del cliente y dice si alguna fila contiene ``texto``."""
        ...

    def rellenar(self, datos: DatosFormulario, canal: CanalEjecucion) -> None:
        """Rellena el formulario de la variante ANES."""
        ...

    def rellenar_axas_ms3(
        self,
        datos: DatosFormulario,
        configuracion: ConfiguracionAxasMs3,
        canal: CanalEjecucion,
    ) -> None:
        """Rellena el formulario de la variante AXAS MS3."""
        ...

    def resumen_formulario(self) -> str: ...

    def guardar(self) -> bytes:
        """Pulsa Guardar y devuelve la captura PNG del resultado."""
        ...

    def cerrar(self) -> None: ...


FabricaNavegador = Callable[[ConfiguracionAltaOportunidad], NavegadorOportunidades]
