"""Caso de uso: lanzar el alta de una oportunidad y atender sus preguntas."""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from gestor_tareas.aplicacion.oportunidad.ejecucion import (
    Ejecucion,
    EstadoEjecucion,
    Opcion,
    TipoPregunta,
    VistaEjecucion,
)
from gestor_tareas.aplicacion.oportunidad.puertos import (
    AutomatizacionFallidaError,
    ConfiguracionAltaInvalidaError,
    FabricaNavegador,
    FuenteConfiguracionAlta,
    NavegadorOportunidades,
)
from gestor_tareas.dominio.oportunidad.entidades import (
    ConfiguracionAltaOportunidad,
    SolicitudAltaOportunidad,
)
from gestor_tareas.dominio.oportunidad.reglas import (
    componer_datos_formulario,
    ddmmaaaa,
    fecha_limite,
    mas_un_mes,
)

_registro = logging.getLogger(__name__)

# Las preguntas del script esperaban sin límite en la terminal; aquí se limita para
# que una pestaña cerrada no deje el navegador (y el siguiente alta) bloqueado.
ESPERA_RESPUESTA_SEGUNDOS = 30 * 60


class AltaEnCursoError(Exception):
    """Ya hay un alta en curso; solo se permite una a la vez."""


class SinEjecucionError(Exception):
    """No se ha lanzado todavía ningún alta (o no tiene lo que se pide)."""


class ConfiguracionNoDisponibleError(Exception):
    """No se puede lanzar el alta porque la configuración local falta o no es válida."""


@dataclass(frozen=True)
class ResumenConfiguracion:
    configuracion: ConfiguracionAltaOportunidad | None
    error: str | None
    fecha_limite: str | None
    fecha_inicio: str


@dataclass(frozen=True)
class _Resultado:
    estado: EstadoEjecucion
    mensaje: str
    captura: bytes | None = None


def _lanzar_en_hilo(tarea: Callable[[], None]) -> None:
    threading.Thread(target=tarea, name="alta-oportunidad", daemon=True).start()


class ServicioAltaOportunidades:
    def __init__(
        self,
        fuente_configuracion: FuenteConfiguracionAlta,
        fabrica_navegador: FabricaNavegador,
        reloj: Callable[[], date] = date.today,
        lanzar: Callable[[Callable[[], None]], None] = _lanzar_en_hilo,
        espera_respuesta_segundos: float = ESPERA_RESPUESTA_SEGUNDOS,
    ) -> None:
        self._fuente = fuente_configuracion
        self._fabrica = fabrica_navegador
        self._reloj = reloj
        self._lanzar = lanzar
        self._espera = espera_respuesta_segundos
        self._cerrojo = threading.Lock()
        self._actual: Ejecucion | None = None

    def resumen_configuracion(self) -> ResumenConfiguracion:
        hoy = self._reloj()
        inicio = ddmmaaaa(mas_un_mes(hoy))
        try:
            configuracion = self._fuente.cargar()
        except ConfiguracionAltaInvalidaError as error:
            return ResumenConfiguracion(None, str(error), None, inicio)
        limite = ddmmaaaa(fecha_limite(hoy, configuracion.dias_fecha_limite))
        return ResumenConfiguracion(configuracion, None, limite, inicio)

    def iniciar(self, solicitud: SolicitudAltaOportunidad) -> VistaEjecucion:
        try:
            configuracion = self._fuente.cargar()
        except ConfiguracionAltaInvalidaError as error:
            raise ConfiguracionNoDisponibleError(f"No se puede lanzar el alta: {error}") from error
        with self._cerrojo:
            if self._actual is not None and not self._actual.instantanea().terminada:
                raise AltaEnCursoError(
                    "Ya hay un alta de oportunidad en curso; espera a que termine."
                )
            ejecucion = Ejecucion(solicitud.prj, self._espera)
            self._actual = ejecucion
        hoy = self._reloj()
        self._lanzar(lambda: self._ejecutar(ejecucion, solicitud, configuracion, hoy))
        return ejecucion.instantanea()

    def estado(self) -> VistaEjecucion:
        return self._ejecucion_actual().instantanea()

    def responder(self, id_pregunta: int, valor: str) -> VistaEjecucion:
        ejecucion = self._ejecucion_actual()
        ejecucion.responder(id_pregunta, valor)
        return ejecucion.instantanea()

    def captura(self) -> bytes:
        captura = self._ejecucion_actual().captura
        if captura is None:
            raise SinEjecucionError("El alta actual no tiene captura del resultado.")
        return captura

    def _ejecucion_actual(self) -> Ejecucion:
        with self._cerrojo:
            if self._actual is None:
                raise SinEjecucionError("Todavía no se ha lanzado ningún alta de oportunidad.")
            return self._actual

    def _ejecutar(
        self,
        ejecucion: Ejecucion,
        solicitud: SolicitudAltaOportunidad,
        configuracion: ConfiguracionAltaOportunidad,
        hoy: date,
    ) -> None:
        # La ejecución solo pasa a terminada cuando el navegador ya se ha cerrado:
        # así un alta lanzada justo después no abre otro Chromium sobre el mismo
        # perfil mientras el anterior aún lo tiene bloqueado.
        navegador: NavegadorOportunidades | None = None
        try:
            navegador = self._fabrica(configuracion)
            resultado = self._recorrer(navegador, ejecucion, solicitud, configuracion, hoy)
        except AutomatizacionFallidaError as error:
            resultado = _Resultado(EstadoEjecucion.ERROR, str(error))
        except Exception as error:  # cualquier fallo se muestra en la página
            _registro.exception("Error inesperado en el alta de %s", solicitud.prj)
            resultado = _Resultado(EstadoEjecucion.ERROR, f"Error inesperado: {error}")
        finally:
            if navegador is not None:
                ejecucion.informar("Cerrando el navegador")
                try:
                    navegador.cerrar()
                except Exception:  # cerrar nunca debe tapar el resultado
                    _registro.exception("No se pudo cerrar el navegador")
        ejecucion.finalizar(resultado.estado, resultado.mensaje, resultado.captura)

    def _recorrer(
        self,
        navegador: NavegadorOportunidades,
        ejecucion: Ejecucion,
        solicitud: SolicitudAltaOportunidad,
        configuracion: ConfiguracionAltaOportunidad,
        hoy: date,
    ) -> "_Resultado":
        ejecucion.informar("Abriendo el navegador")
        navegador.abrir()
        descripcion = solicitud.descripcion
        if descripcion is None:
            ejecucion.informar(f"Buscando la descripción de {solicitud.prj} en Notion")
            descripcion = navegador.buscar_descripcion(solicitud.prj, ejecucion)
        datos = componer_datos_formulario(solicitud, descripcion, hoy, configuracion)
        ejecucion.informar(f"Nombre de la oportunidad: {datos.nombre}")

        navegador.iniciar_sesion(ejecucion)
        navegador.cambiar_perfil(ejecucion)
        if navegador.existe_oportunidad(solicitud.prj):
            respuesta = ejecucion.preguntar(
                TipoPregunta.DUPLICADO,
                f"Ya existe una oportunidad con {solicitud.prj}. ¿Crear otra igualmente?",
                (Opcion("si", "Sí, crear otra"), Opcion("no", "No")),
            )
            if respuesta != "si":
                return _Resultado(
                    EstadoEjecucion.NO_GUARDADA, "No se ha creado ninguna oportunidad."
                )
        else:
            ejecucion.informar(f"No existe ninguna oportunidad {solicitud.prj}: no habrá duplicado")

        navegador.rellenar(datos, ejecucion)
        respuesta = ejecucion.preguntar(
            TipoPregunta.GUARDAR,
            "Revisa los valores del formulario (también en la ventana del navegador). "
            "¿Guardar la oportunidad?",
            (Opcion("guardar", "Guardar"), Opcion("no_guardar", "No guardar")),
            detalle=navegador.resumen_formulario(),
        )
        if respuesta != "guardar":
            return _Resultado(EstadoEjecucion.NO_GUARDADA, "No se ha guardado nada.")
        ejecucion.informar("Guardando la oportunidad")
        captura = navegador.guardar()
        return _Resultado(
            EstadoEjecucion.GUARDADA,
            "Oportunidad guardada. Revisa la captura del resultado.",
            captura,
        )
