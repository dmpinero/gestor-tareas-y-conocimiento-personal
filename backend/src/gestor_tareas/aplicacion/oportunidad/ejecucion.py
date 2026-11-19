"""Estado de una ejecución del alta, compartido entre el hilo del navegador y la API."""

import threading
import uuid
from dataclasses import dataclass
from enum import StrEnum

from gestor_tareas.aplicacion.oportunidad.puertos import AutomatizacionFallidaError


class EstadoEjecucion(StrEnum):
    EN_CURSO = "en_curso"
    GUARDADA = "guardada"
    NO_GUARDADA = "no_guardada"
    ERROR = "error"


class TipoPregunta(StrEnum):
    INICIO_SESION = "inicio_sesion"
    DUPLICADO = "duplicado"
    INTERVENCION_MANUAL = "intervencion_manual"
    GUARDAR = "guardar"


@dataclass(frozen=True)
class Opcion:
    valor: str
    etiqueta: str


@dataclass(frozen=True)
class Pregunta:
    id: int
    tipo: TipoPregunta
    mensaje: str
    opciones: tuple[Opcion, ...] = ()
    detalle: str | None = None


@dataclass(frozen=True)
class VistaEjecucion:
    id: str
    prj: str
    estado: EstadoEjecucion
    pasos: tuple[str, ...]
    pregunta: Pregunta | None
    mensaje_final: str | None
    hay_captura: bool

    @property
    def terminada(self) -> bool:
        return self.estado is not EstadoEjecucion.EN_CURSO


class SinPreguntaPendienteError(Exception):
    """La respuesta no corresponde a la pregunta pendiente (o no hay ninguna)."""


class OpcionNoValidaError(ValueError):
    """La respuesta no es una de las opciones de la pregunta."""


class Ejecucion:
    """Una ejecución del alta: pasos, pregunta pendiente y resultado.

    El hilo del navegador escribe en ella y se bloquea en ``preguntar`` hasta que
    la API llama a ``responder``; la API solo lee instantáneas inmutables.
    """

    def __init__(self, prj: str, espera_respuesta_segundos: float) -> None:
        self.id = uuid.uuid4().hex
        self._prj = prj
        self._espera = espera_respuesta_segundos
        self._condicion = threading.Condition()
        self._estado = EstadoEjecucion.EN_CURSO
        self._pasos: list[str] = []
        self._pregunta: Pregunta | None = None
        self._respuesta: str | None = None
        self._siguiente_id = 1
        self._mensaje_final: str | None = None
        self._captura: bytes | None = None

    # --- Lado de la API ------------------------------------------------------------
    def instantanea(self) -> VistaEjecucion:
        with self._condicion:
            return VistaEjecucion(
                id=self.id,
                prj=self._prj,
                estado=self._estado,
                pasos=tuple(self._pasos),
                pregunta=self._pregunta,
                mensaje_final=self._mensaje_final,
                hay_captura=self._captura is not None,
            )

    @property
    def captura(self) -> bytes | None:
        with self._condicion:
            return self._captura

    def responder(self, id_pregunta: int, valor: str) -> None:
        with self._condicion:
            pregunta = self._pregunta
            if pregunta is None or pregunta.id != id_pregunta or not pregunta.opciones:
                raise SinPreguntaPendienteError(
                    "No hay ninguna pregunta pendiente que admita esa respuesta."
                )
            if valor not in {opcion.valor for opcion in pregunta.opciones}:
                raise OpcionNoValidaError(f"'{valor}' no es una respuesta válida a la pregunta.")
            self._respuesta = valor
            self._pregunta = None
            self._condicion.notify_all()

    # --- Lado del navegador (CanalEjecucion) ------------------------------------------
    def informar(self, paso: str) -> None:
        with self._condicion:
            self._pasos.append(paso)

    def mostrar_espera_inicio_sesion(self, mensaje: str) -> None:
        with self._condicion:
            self._pregunta = self._nueva_pregunta(TipoPregunta.INICIO_SESION, mensaje, (), None)

    def ocultar_espera(self) -> None:
        with self._condicion:
            if self._pregunta is not None and not self._pregunta.opciones:
                self._pregunta = None

    def pedir_intervencion(self, mensaje: str) -> None:
        self.preguntar(
            TipoPregunta.INTERVENCION_MANUAL, mensaje, (Opcion("continuar", "Continuar"),)
        )

    def preguntar(
        self,
        tipo: TipoPregunta,
        mensaje: str,
        opciones: tuple[Opcion, ...],
        detalle: str | None = None,
    ) -> str:
        """Publica la pregunta y bloquea hasta la respuesta (o hasta agotar la espera)."""
        with self._condicion:
            self._respuesta = None
            self._pregunta = self._nueva_pregunta(tipo, mensaje, opciones, detalle)
            respondida = self._condicion.wait_for(
                lambda: self._respuesta is not None, timeout=self._espera
            )
            if not respondida:
                self._pregunta = None
                raise AutomatizacionFallidaError(
                    "No se recibió respuesta a tiempo en la página; no se ha guardado nada."
                )
            respuesta, self._respuesta = str(self._respuesta), None
            return respuesta

    def finalizar(
        self, estado: EstadoEjecucion, mensaje: str, captura: bytes | None = None
    ) -> None:
        with self._condicion:
            self._estado = estado
            self._mensaje_final = mensaje
            self._captura = captura
            self._pregunta = None

    def _nueva_pregunta(
        self,
        tipo: TipoPregunta,
        mensaje: str,
        opciones: tuple[Opcion, ...],
        detalle: str | None,
    ) -> Pregunta:
        pregunta = Pregunta(self._siguiente_id, tipo, mensaje, opciones, detalle)
        self._siguiente_id += 1
        return pregunta
