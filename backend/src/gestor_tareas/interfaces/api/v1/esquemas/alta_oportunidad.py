from decimal import Decimal

from pydantic import BaseModel, Field

from gestor_tareas.aplicacion.oportunidad.ejecucion import (
    EstadoEjecucion,
    TipoPregunta,
    VistaEjecucion,
)
from gestor_tareas.aplicacion.oportunidad.servicio import (
    ResumenConfiguracion,
    ResumenConfiguracionAxasMs3,
)
from gestor_tareas.dominio.oportunidad.entidades import (
    NOMBRE_MENU_AXAS_MS3_PREDETERMINADO,
    NOMBRE_MENU_PREDETERMINADO,
    ConfiguracionAltaOportunidad,
    ConfiguracionAxasMs3,
)


class SolicitudAltaEsquema(BaseModel):
    """Campos variables del alta. Las reglas (formato del PRJ, obligatorios) se
    validan en el dominio para devolver siempre su mensaje exacto."""

    prj: str = Field(max_length=20, examples=["PRJ-00001"])
    descripcion: str | None = Field(
        default=None,
        max_length=500,
        description="Si se omite o va vacía, se busca en Notion.",
    )
    duracion: int | None = Field(default=None, description="Duración en meses.")
    importe: Decimal | None = Field(default=None, description="Importe total previsto (EUR).")
    coste: Decimal | None = Field(default=None, description="Coste total previsto (EUR).")


class SolicitudAltaAxasMs3Esquema(BaseModel):
    """Campos variables del alta AXAS MS3. La descripción es obligatoria, pero se
    valida en el dominio (como el resto de reglas) para devolver su mensaje exacto."""

    codigo_servicio: str = Field(max_length=50, examples=["AXAS0024"])
    descripcion: str | None = Field(
        default=None, max_length=500, description="Obligatoria; no se busca en Notion."
    )
    duracion: int | None = Field(default=None, description="Duración en meses.")
    importe: Decimal | None = Field(default=None, description="Importe total previsto (EUR).")
    coste: Decimal | None = Field(default=None, description="Coste total previsto (EUR).")


class AsignacionEsquema(BaseModel):
    nombre: str
    porcentaje: str


class ValoresFijosEsquema(BaseModel):
    perfil: str
    cliente: str
    grupo: str
    tipo: str
    segmentacion: str
    fase: str
    probabilidad: str
    dias_fecha_limite: int
    tipo_servicio: str
    lineas_negocio: list[AsignacionEsquema]
    comunidades: list[AsignacionEsquema]

    @classmethod
    def _campos(cls, c: ConfiguracionAltaOportunidad | ConfiguracionAxasMs3) -> dict:
        return {
            "perfil": c.perfil,
            "cliente": c.cliente,
            "grupo": c.grupo,
            "tipo": c.tipo,
            "segmentacion": c.segmentacion,
            "fase": c.fase,
            "probabilidad": c.probabilidad,
            "dias_fecha_limite": c.dias_fecha_limite,
            "tipo_servicio": c.tipo_servicio,
            "lineas_negocio": [AsignacionEsquema(**vars(a)) for a in c.lineas_negocio],
            "comunidades": [AsignacionEsquema(**vars(a)) for a in c.comunidades],
        }


class ValoresFijosAxasMs3Esquema(ValoresFijosEsquema):
    responsable_operaciones: str
    responsable_tecnico: str
    area_ms3: str


class ResumenConfiguracionEsquema(BaseModel):
    valores: ValoresFijosEsquema | None = Field(
        description="Valores fijos de la configuración local; null si no es válida."
    )
    error: str | None = Field(description="Por qué no se puede lanzar el alta, si es el caso.")
    fecha_limite: str | None = Field(description="Hoy + días de la configuración (dd/mm/aaaa).")
    fecha_inicio: str = Field(description="Hoy + 1 mes (dd/mm/aaaa).")
    nombre_menu: str = Field(
        description=(
            "Nombre de la entrada del menú; el predeterminado si la configuración no es válida."
        )
    )

    @classmethod
    def desde(cls, resumen: ResumenConfiguracion) -> "ResumenConfiguracionEsquema":
        c = resumen.configuracion
        valores = None if c is None else ValoresFijosEsquema(**ValoresFijosEsquema._campos(c))
        return cls(
            valores=valores,
            error=resumen.error,
            fecha_limite=resumen.fecha_limite,
            fecha_inicio=resumen.fecha_inicio,
            nombre_menu=NOMBRE_MENU_PREDETERMINADO if c is None else c.nombre_menu,
        )


class ResumenConfiguracionAxasMs3Esquema(ResumenConfiguracionEsquema):
    """Como el resumen de ANES, con los valores fijos propios de AXAS MS3."""

    valores: ValoresFijosAxasMs3Esquema | None = Field(  # type: ignore[assignment]
        description="Valores fijos del bloque axas_ms3; null si falta o no es válido."
    )

    @classmethod
    def desde_axas_ms3(
        cls, resumen: ResumenConfiguracionAxasMs3
    ) -> "ResumenConfiguracionAxasMs3Esquema":
        c = resumen.configuracion
        valores = (
            None
            if c is None
            else ValoresFijosAxasMs3Esquema(
                **ValoresFijosEsquema._campos(c),
                responsable_operaciones=c.responsable_operaciones,
                responsable_tecnico=c.responsable_tecnico,
                area_ms3=c.area_ms3,
            )
        )
        return cls(
            valores=valores,
            error=resumen.error,
            fecha_limite=resumen.fecha_limite,
            fecha_inicio=resumen.fecha_inicio,
            nombre_menu=NOMBRE_MENU_AXAS_MS3_PREDETERMINADO if c is None else c.nombre_menu,
        )


class OpcionEsquema(BaseModel):
    valor: str
    etiqueta: str


class PreguntaEsquema(BaseModel):
    id: int
    tipo: TipoPregunta
    mensaje: str
    detalle: str | None
    opciones: list[OpcionEsquema] = Field(
        description="Respuestas posibles; vacía si solo hay que actuar en el navegador."
    )


class EjecucionEsquema(BaseModel):
    id: str
    prj: str
    estado: EstadoEjecucion
    terminada: bool
    pasos: list[str]
    pregunta: PreguntaEsquema | None
    mensaje_final: str | None
    hay_captura: bool

    @classmethod
    def desde(cls, vista: VistaEjecucion) -> "EjecucionEsquema":
        p = vista.pregunta
        pregunta = (
            None
            if p is None
            else PreguntaEsquema(
                id=p.id,
                tipo=p.tipo,
                mensaje=p.mensaje,
                detalle=p.detalle,
                opciones=[OpcionEsquema(valor=o.valor, etiqueta=o.etiqueta) for o in p.opciones],
            )
        )
        return cls(
            id=vista.id,
            prj=vista.prj,
            estado=vista.estado,
            terminada=vista.terminada,
            pasos=list(vista.pasos),
            pregunta=pregunta,
            mensaje_final=vista.mensaje_final,
            hay_captura=vista.hay_captura,
        )


class RespuestaPreguntaEsquema(BaseModel):
    id_pregunta: int
    valor: str = Field(max_length=50)
