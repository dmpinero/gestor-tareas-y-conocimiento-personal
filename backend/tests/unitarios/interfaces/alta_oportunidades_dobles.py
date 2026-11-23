"""Dobles y utilidades compartidos por los tests de la API del automatizador.

Ningún test abre un navegador real: el puerto del navegador se sustituye por
``NavegadorSimulado``, que imita sus pasos y sus preguntas. Solo valores falsos.
"""

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import date

from fastapi.testclient import TestClient
from httpx import Response

from gestor_tareas.aplicacion.oportunidad.puertos import (
    AutomatizacionFallidaError,
    CanalEjecucion,
    ConfiguracionAltaInvalidaError,
    FuenteConfiguracionAlta,
)
from gestor_tareas.aplicacion.oportunidad.servicio import ServicioAltaOportunidades
from gestor_tareas.dominio.oportunidad.entidades import (
    Asignacion,
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
    DatosFormulario,
)
from gestor_tareas.interfaces.api.v1.enrutadores.alta_oportunidades import obtener_servicio
from gestor_tareas.main_automatizador import crear_aplicacion_automatizador

RUTA = "/api/v1/alta-oportunidades"
CAPTURA_PNG = b"\x89PNG\r\n\x1a\nresultado"

CONFIGURACION = ConfiguracionAltaOportunidad(
    url_digital_desktop="https://crm.ejemplo.invalid/",
    url_notion="https://notas.ejemplo.invalid/proyectos",
    titulo_pagina_notion="Proyectos de ejemplo",
    perfil="Persona Ejemplo",
    cliente_busqueda="Cliente Ejemplo",
    cliente="[CEJ] Cliente Ejemplo S.A.",
    grupo="Grupo Ejemplo",
    tipo="Tipo Ejemplo",
    segmentacion="Segmentación Ejemplo",
    fase="1 - Fase Ejemplo",
    probabilidad="50",
    dias_fecha_limite=7,
    tipo_servicio="Servicio Ejemplo",
    lineas_negocio=(Asignacion("Línea Ejemplo", "100"),),
    comunidades=(Asignacion("Comunidad A", "80"), Asignacion("Comunidad B", "20")),
)

SOLICITUD = {"prj": "PRJ-00001", "duracion": 2, "importe": 10000, "coste": 8500}

CONFIGURACION_MS3 = ConfiguracionAxasMs3(
    perfil="Persona Ms3",
    responsable_busqueda="Persona",
    cliente_busqueda="Cliente Ms3",
    cliente="[CMS] Cliente Ms3 S.A.",
    grupo="Grupo Ms3",
    tipo="Tipo Ms3",
    responsable_operaciones="Responsable Operaciones Ejemplo",
    responsable_tecnico="Responsable Técnico Ejemplo",
    responsable_tecnico_busqueda=None,
    segmentacion="Segmentación Ms3",
    area_ms3="Área Ejemplo",
    fase="1 - Fase Ms3",
    probabilidad="60",
    dias_fecha_limite=10,
    tipo_servicio="Servicio Ms3",
    lineas_negocio=(Asignacion("Línea Ms3", "100"),),
    comunidades=(Asignacion("Comunidad X", "80"), Asignacion("Comunidad Y", "20")),
)
CONFIGURACION_CON_MS3 = replace(CONFIGURACION, axas_ms3=CONFIGURACION_MS3)

RUTA_MS3 = f"{RUTA}/axas-ms3"
SOLICITUD_MS3 = {
    "codigo_servicio": "AXAS0024",
    "descripcion": "Migración portal",
    "duracion": 2,
    "importe": 10000,
    "coste": 8500,
}
NOMBRE_MS3 = "AXAS-MS3-EV-24-Migración portal"


@dataclass
class NavegadorSimulado:
    """Doble del navegador: registra cada paso en ``llamadas`` y simula esperas y fallos."""

    existe: bool = False
    pedir_intervencion: bool = False
    esperar_inicio_sesion: bool = False
    error_al_iniciar_sesion: str | None = None
    fallo_en: str | None = None
    bloquear_abrir: threading.Event | None = None
    bloquear_cerrar: threading.Event | None = None
    liberar_inicio_sesion: threading.Event = field(default_factory=threading.Event)
    llamadas: list[str] = field(default_factory=list)
    datos: DatosFormulario | None = None
    configuracion_ms3: ConfiguracionAxasMs3 | None = None
    perfil: str | None = None
    busqueda_duplicado: tuple[str, str, str] | None = None
    cerrado: bool = False

    def _paso(self, nombre: str) -> None:
        self.llamadas.append(nombre)
        if self.fallo_en == nombre:
            raise RuntimeError(f"Fallo simulado en {nombre}")

    def abrir(self) -> None:
        if self.bloquear_abrir is not None:
            self.bloquear_abrir.wait(5)
        self._paso("abrir")

    def buscar_descripcion(self, prj: str, canal: CanalEjecucion) -> str:
        self._paso("buscar_descripcion")
        return "Descripción desde las notas"

    def iniciar_sesion(self, canal: CanalEjecucion) -> None:
        self._paso("iniciar_sesion")
        if self.error_al_iniciar_sesion:
            raise AutomatizacionFallidaError(self.error_al_iniciar_sesion)
        if self.esperar_inicio_sesion:
            canal.mostrar_espera_inicio_sesion("Inicia sesión en la ventana del navegador.")
            self.liberar_inicio_sesion.wait(5)
            canal.ocultar_espera()
        canal.informar("Sesión iniciada")

    def cambiar_perfil(self, perfil: str, canal: CanalEjecucion) -> None:
        self.perfil = perfil
        self._paso("cambiar_perfil")
        if self.pedir_intervencion:
            canal.pedir_intervencion("No pude confirmar el cambio de perfil. Cámbialo tú a mano.")
        canal.informar("Perfil activo")

    def existe_oportunidad(self, cliente: str, cliente_busqueda: str, texto: str) -> bool:
        self.busqueda_duplicado = (cliente, cliente_busqueda, texto)
        self._paso("existe_oportunidad")
        return self.existe

    def rellenar(self, datos: DatosFormulario, canal: CanalEjecucion) -> None:
        self.datos = datos
        self._paso("rellenar")
        canal.informar("Datos de la oportunidad")

    def rellenar_axas_ms3(
        self,
        datos: DatosFormulario,
        configuracion: ConfiguracionAxasMs3,
        canal: CanalEjecucion,
    ) -> None:
        self.datos = datos
        self.configuracion_ms3 = configuracion
        self._paso("rellenar_axas_ms3")
        canal.informar("Datos de la oportunidad")

    def resumen_formulario(self) -> str:
        self._paso("resumen_formulario")
        return "Nombre: PRJ-00001 Descripción desde las notas"

    def guardar(self) -> bytes:
        self.llamadas.append("guardar")
        return CAPTURA_PNG

    def cerrar(self) -> None:
        self.llamadas.append("cerrar")
        if self.bloquear_cerrar is not None:
            self.bloquear_cerrar.wait(5)
        self.cerrado = True


class FuenteFija:
    def __init__(self, configuracion: ConfiguracionAltaOportunidad = CONFIGURACION) -> None:
        self._configuracion = configuracion

    def cargar(self) -> ConfiguracionAltaOportunidad:
        return self._configuracion


class FuenteRota:
    def cargar(self) -> ConfiguracionAltaOportunidad:
        raise ConfiguracionAltaInvalidaError(
            "No existe el archivo de configuración /config/x.json."
        )


def montar_cliente(
    fuente: FuenteConfiguracionAlta | None = None,
    espera_respuesta_segundos: float = 5,
    hoy: date = date(2026, 1, 31),
    opciones_navegador: dict[str, object] | None = None,
    **opciones: object,
) -> tuple[TestClient, list[NavegadorSimulado], ServicioAltaOportunidades]:
    """Aplicación del automatizador con un servicio propio y navegadores simulados.

    Cada alta crea un ``NavegadorSimulado`` con ``opciones``; si se pasa
    ``opciones_navegador``, se lee al crear cada navegador (puede cambiarse luego).
    """
    navegadores: list[NavegadorSimulado] = []
    if opciones_navegador is None:
        opciones_navegador = {}
    opciones_navegador.update(opciones)

    def fabrica(_configuracion: ConfiguracionAltaOportunidad) -> NavegadorSimulado:
        navegador = NavegadorSimulado(**opciones_navegador)  # type: ignore[arg-type]
        navegadores.append(navegador)
        return navegador

    servicio = ServicioAltaOportunidades(
        fuente or FuenteFija(),
        fabrica,
        reloj=lambda: hoy,
        espera_respuesta_segundos=espera_respuesta_segundos,
    )
    aplicacion = crear_aplicacion_automatizador()
    aplicacion.dependency_overrides[obtener_servicio] = lambda: servicio
    return TestClient(aplicacion), navegadores, servicio


def esperar(cliente: TestClient, condicion: Callable[[dict], bool], limite: float = 5) -> dict:
    fin = time.monotonic() + limite
    estado: dict = {}
    while time.monotonic() < fin:
        estado = cliente.get(f"{RUTA}/ejecucion").json()
        if condicion(estado):
            return estado
        time.sleep(0.02)
    raise AssertionError(f"La ejecución no llegó al estado esperado: {estado}")


def esperar_pregunta(cliente: TestClient, tipo: str) -> dict:
    return esperar(cliente, lambda e: (e["pregunta"] or {}).get("tipo") == tipo)


def esperar_fin(cliente: TestClient, limite: float = 5) -> dict:
    return esperar(cliente, lambda e: e["terminada"], limite)


def enviar_respuesta(cliente: TestClient, id_pregunta: int, valor: str) -> Response:
    return cliente.post(
        f"{RUTA}/ejecucion/respuesta", json={"id_pregunta": id_pregunta, "valor": valor}
    )


def responder(cliente: TestClient, estado: dict, valor: str) -> None:
    respuesta = enviar_respuesta(cliente, estado["pregunta"]["id"], valor)
    assert respuesta.status_code == 200, respuesta.text
