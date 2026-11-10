import re
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
    model_validator,
)

from gestor_tareas.dominio.tarea.entidades import TipoTarea
from gestor_tareas.interfaces.api.v1.esquemas.texto import (
    PATRON_NO_VACIO,
    TextoObligatorio,
    recortar_espacios,
)

# Fecha y hora local en ISO 8601 sin zona horaria: "YYYY-MM-DDTHH:MM:SS", con una
# fracción de segundo opcional que se descarta. El patrón solo admite fechas reales
# del calendario (incluido el 29 de febrero de los años bisiestos) para que el
# contrato OpenAPI describa exactamente lo que acepta la API.
_ANIO = r"(?:\d{3}[1-9]|\d{2}[1-9]\d|\d[1-9]\d{2}|[1-9]\d{3})"
_ANIO_BISIESTO = r"(?:\d{2}(?:0[48]|[2468][048]|[13579][26])|(?:0[48]|[2468][048]|[13579][26])00)"
_FECHA = (
    rf"(?:{_ANIO}-(?:(?:0[13578]|1[02])-(?:0[1-9]|[12]\d|3[01])"
    r"|(?:0[469]|11)-(?:0[1-9]|[12]\d|30)"
    r"|02-(?:0[1-9]|1\d|2[0-8]))"
    rf"|{_ANIO_BISIESTO}-02-29)"
)
_HORA = r"(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?"
PATRON_FECHA_HORA = rf"^{_FECHA}T{_HORA}$"
_PATRON_FECHA_HORA = re.compile(PATRON_FECHA_HORA)


def _validar_fecha_hora(valor: object) -> datetime:
    """Convierte la fecha y hora recibida en un ``datetime`` sin zona horaria.

    Es la hora local tal como la escribe la persona usuaria. Un
    valor con zona horaria (``Z`` o ``+01:00``) se rechaza con 422 en vez de
    convertirlo, porque no hay una zona de referencia a la que traducirlo. La
    precisión es de segundos, como el formulario y la columna ``DATETIME``: los
    microsegundos se descartan para que la respuesta salga siempre como
    ``YYYY-MM-DDTHH:MM:SS``.
    """
    if isinstance(valor, datetime) and valor.tzinfo is None:
        return valor.replace(microsecond=0)
    if not isinstance(valor, str) or not _PATRON_FECHA_HORA.fullmatch(valor):
        raise ValueError("La fecha y hora debe tener el formato YYYY-MM-DDTHH:MM:SS sin zona")
    return datetime.fromisoformat(valor).replace(microsecond=0)


FechaHoraLocal = Annotated[
    datetime,
    PlainValidator(_validar_fecha_hora),
    PlainSerializer(
        lambda valor: valor.isoformat(timespec="seconds"), return_type=str, when_used="json"
    ),
    WithJsonSchema(
        {
            "type": "string",
            "pattern": PATRON_FECHA_HORA,
            "description": "Fecha y hora local sin zona horaria (YYYY-MM-DDTHH:MM:SS).",
            "examples": ["2026-11-09T10:30:00"],
        }
    ),
]


# Nombres de etiqueta y de persona: mismo enfoque que `nombre` (recorte con los
# espacios de JSON Schema y `pattern: "\\S"` publicado en cada elemento).
NombreEtiqueta = Annotated[
    TextoObligatorio, Field(min_length=1, max_length=50, json_schema_extra=PATRON_NO_VACIO)
]
NombrePersona = Annotated[
    TextoObligatorio, Field(min_length=1, max_length=100, json_schema_extra=PATRON_NO_VACIO)
]


def _normalizar_prioridad(valor: object) -> object:
    """Aplica la semántica de `integer` de JSON Schema.

    `3.0` es un entero válido y se convierte en 3; los booleanos no son enteros
    (en Python `True` es un `int`, así que se rechazan explícitamente). El resto
    lo valida `int` en modo estricto, que rechaza cadenas como `"2"` y `2.5`.
    """
    if isinstance(valor, bool):
        raise ValueError("La prioridad debe ser un número entero.")
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


# Los límites van antes del `BeforeValidator`: en el orden inverso Pydantic
# publica `ge`/`le` en el JSON Schema en lugar de `minimum`/`maximum`.
PrioridadEntera = Annotated[
    int, Field(strict=True, ge=1, le=5), BeforeValidator(_normalizar_prioridad)
]


def _texto_opcional(valor: object) -> object:
    """Recorta el texto como los obligatorios; si queda vacío, se guarda ``None``.

    Así un texto vacío o formado solo por espacios equivale a no indicarlo, y la
    API no guarda ni devuelve cadenas vacías en los campos opcionales.
    """
    recortado = recortar_espacios(valor)
    return None if recortado == "" else recortado


# El límite se aplica tras recortar y solo al texto; `None` siempre se admite.
DescripcionOportunidad = Annotated[
    Annotated[str, Field(max_length=200)] | None, BeforeValidator(_texto_opcional)
]
ObservacionesOportunidad = Annotated[
    Annotated[str, Field(max_length=5000)] | None, BeforeValidator(_texto_opcional)
]


class OportunidadEsquema(BaseModel):
    """Datos de una tarea de tipo oportunidad."""

    codigo: TextoObligatorio = Field(min_length=1, max_length=10, json_schema_extra=PATRON_NO_VACIO)
    descripcion: DescripcionOportunidad = Field(
        default=None, description="Opcional. Vacía o solo con espacios se guarda como null."
    )
    observaciones: ObservacionesOportunidad = Field(
        default=None, description="Opcional. Vacías o solo con espacios se guardan como null."
    )


class OportunidadSalidaEsquema(BaseModel):
    codigo: str
    descripcion: str | None
    observaciones: str | None


def _validar_tipo_tarea(valor: object) -> TipoTarea:
    """Solo admite los valores de `TipoTarea` como cadenas (otro valor → 422)."""
    if not isinstance(valor, str):
        raise ValueError("El tipo de tarea debe ser una cadena.")
    return TipoTarea(valor)


# Se publica en línea con sus valores. El tipo anotado es `str` (y no el enum)
# porque FastAPI registra como componente del contrato cualquier `Enum` que
# encuentre en las anotaciones, aunque nada lo referencie, y con la documentación
# interna del dominio. El valor validado sí es un `TipoTarea` (un `StrEnum`, que
# también es `str`).
TipoTareaEsquema = Annotated[
    str,
    PlainValidator(_validar_tipo_tarea),
    WithJsonSchema({"type": "string", "enum": [tipo.value for tipo in TipoTarea]}),
]


# Campo con los datos de cada tipo de tarea. Un tipo nuevo añade aquí su campo
# (con su esquema en `TareaCrearEsquema`) y la regla de abajo se aplica sola.
_CAMPO_DE_DATOS_POR_TIPO: dict[TipoTarea, str] = {TipoTarea.OPORTUNIDAD: "oportunidad"}


def _regla_tipo_y_datos_en_el_contrato() -> dict:
    """Publica en el contrato la regla que valida `_datos_segun_el_tipo`.

    Cada rama del `anyOf` es un caso válido: sin tipo y sin los datos de ningún
    tipo, o un tipo con sus datos obligatorios (y sin los de los demás tipos).
    """
    # `{"type": "null"}` y no `{"const": None}`: FastAPI quita los valores None al
    # generar el OpenAPI, y `const` desaparecería.
    nulo = {"type": "null"}
    campos = _CAMPO_DE_DATOS_POR_TIPO.values()
    sin_tipo = {"properties": {"tipo": nulo, **{c: nulo for c in campos}}}
    ramas = [sin_tipo]
    for tipo, campo in _CAMPO_DE_DATOS_POR_TIPO.items():
        otros = {otro: nulo for otro in campos if otro != campo}
        ramas.append(
            {
                "properties": {"tipo": {"const": tipo.value}, campo: {"type": "object"}, **otros},
                "required": ["tipo", campo],
            }
        )
    return {"anyOf": ramas}


class TareaCrearEsquema(BaseModel):
    model_config = ConfigDict(json_schema_extra=_regla_tipo_y_datos_en_el_contrato())

    nombre: TextoObligatorio = Field(
        min_length=1, max_length=200, json_schema_extra=PATRON_NO_VACIO
    )
    prioridad: PrioridadEntera | None = None
    descripcion: TextoObligatorio = Field(
        min_length=1, max_length=500, json_schema_extra=PATRON_NO_VACIO
    )
    fecha_creacion: FechaHoraLocal
    fecha_vencimiento: FechaHoraLocal | None = Field(
        default=None,
        description="Opcional. Si se indica, no puede ser anterior a fecha_creacion (422).",
    )
    etiquetas: list[NombreEtiqueta] = Field(default_factory=list)
    asignados: list[NombrePersona] = Field(default_factory=list)
    tipo: TipoTareaEsquema | None = Field(
        default=None, description="Opcional. Con un tipo, sus datos son obligatorios (422)."
    )
    oportunidad: OportunidadEsquema | None = Field(
        default=None,
        description='Obligatoria si tipo es "oportunidad"; si no, debe ser null (422).',
    )

    @model_validator(mode="after")
    def _datos_segun_el_tipo(self) -> Self:
        for tipo, campo in _CAMPO_DE_DATOS_POR_TIPO.items():
            tiene_datos = getattr(self, campo) is not None
            if self.tipo is tipo and not tiene_datos:
                raise ValueError(
                    f"Los datos de la {campo} son obligatorios si el tipo es «{tipo.value}»."
                )
            if self.tipo is not tipo and tiene_datos:
                raise ValueError(
                    f"Los datos de la {campo} solo se admiten si el tipo es «{tipo.value}»."
                )
        return self

    @model_validator(mode="after")
    def _vencimiento_no_anterior_a_creacion(self) -> Self:
        # JSON Schema no puede comparar dos campos: la regla solo se documenta en
        # la descripción de `fecha_vencimiento` del contrato OpenAPI.
        if self.fecha_vencimiento is not None and self.fecha_vencimiento < self.fecha_creacion:
            raise ValueError(
                "La fecha de vencimiento no puede ser anterior a la fecha de creación."
            )
        return self


class TareaActualizarEsquema(TareaCrearEsquema):
    """Cuerpo de la edición: los mismos campos y validaciones que el alta.

    Ni el alta ni la edición reciben ``completada`` ni ``pasos_oportunidad``: como
    cualquier campo desconocido, se descartan. El estado solo cambia con
    ``TareaCompletadaEsquema`` y el de cada paso con ``PasoHechoEsquema``.
    """


class TareaCompletadaEsquema(BaseModel):
    """Cuerpo del cambio de estado. Solo admite ``true`` o ``false`` de JSON: una
    cadena como ``"true"``, un número o ``null`` se rechazan con 422."""

    completada: bool = Field(strict=True)


class PasoHechoEsquema(BaseModel):
    """Cuerpo del cambio de estado de un paso de una oportunidad. Solo admite
    ``true`` o ``false`` de JSON: una cadena, un número o ``null`` se rechazan con
    422."""

    hecho: bool = Field(strict=True)


class PasoOportunidadSalidaEsquema(BaseModel):
    """Paso de una oportunidad, copiado del workflow al crearla, con su avance."""

    id: int
    numero: int
    nombre: str
    hecho: bool


class TareaSalidaEsquema(BaseModel):
    id: int
    nombre: str
    prioridad: int | None
    descripcion: str
    fecha_creacion: FechaHoraLocal
    fecha_vencimiento: FechaHoraLocal | None
    etiquetas: list[str]
    asignados: list[str]
    tipo: TipoTareaEsquema | None
    oportunidad: OportunidadSalidaEsquema | None
    completada: bool
    pasos_oportunidad: list[PasoOportunidadSalidaEsquema] = Field(
        description="Pasos de la oportunidad por número; vacía si no es oportunidad "
        "o no tiene pasos."
    )
