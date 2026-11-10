/**
 * Tipos de tarea. Cada tipo tiene sus propios campos: añadir uno nuevo es
 * sumar su valor aquí y en `TIPOS_TAREA`, más su bloque en el formulario y en
 * el detalle.
 */
export type TipoTarea = 'oportunidad'

/** Tipos de tarea con su texto visible, en el orden en que se ofrecen. */
export const TIPOS_TAREA: readonly { valor: TipoTarea; etiqueta: string }[] = [
  { valor: 'oportunidad', etiqueta: 'Oportunidad' },
]

/** Texto visible de un tipo de tarea, o `null` si la tarea no tiene tipo. */
export function etiquetaTipoTarea(tipo: TipoTarea | null): string | null {
  return TIPOS_TAREA.find((elemento) => elemento.valor === tipo)?.etiqueta ?? null
}

/** Campos propios de una tarea de tipo "Oportunidad". */
export interface Oportunidad {
  /** De 1 a 10 caracteres. */
  codigo: string
  /** Hasta 200 caracteres; `null` si no tiene. */
  descripcion: string | null
  /** Hasta 5000 caracteres; `null` si no tiene. */
  observaciones: string | null
}

/**
 * Tarea tal como la devuelve la API (`GET`/`POST /tareas`, `PUT /tareas/{id}`,
 * `PATCH /tareas/{id}/completada`).
 */
export interface Tarea {
  id: number
  nombre: string
  prioridad: number | null
  descripcion: string
  /** ISO 8601 sin zona horaria (`YYYY-MM-DDTHH:MM:SS`), en hora local. */
  fecha_creacion: string
  /** Mismo formato que `fecha_creacion`; `null` si la tarea no vence. */
  fecha_vencimiento: string | null
  /** Nombres de las etiquetas, en orden alfabético. */
  etiquetas: string[]
  /** Nombres de las personas asignadas, en orden alfabético. */
  asignados: string[]
  /** `null` si la tarea no tiene tipo. */
  tipo: TipoTarea | null
  /** Datos de la oportunidad si `tipo` es `"oportunidad"`; si no, `null`. */
  oportunidad: Oportunidad | null
  /** `true` si la tarea está completada. Solo cambia con
   * `PATCH /tareas/{id}/completada`; `POST` y `PUT` no lo reciben. */
  completada: boolean
}

/**
 * Cuerpo de `POST /tareas` y `PUT /tareas/{id}`. La prioridad va de 1 (más
 * prioritaria) a 5; las fechas son ISO 8601 sin zona horaria. Las etiquetas y
 * personas que no existan se crean al guardar. `oportunidad` es obligatoria
 * si `tipo` es `"oportunidad"` y debe ser `null` si la tarea no tiene tipo.
 */
export interface DatosTarea {
  nombre: string
  prioridad: number | null
  descripcion: string
  fecha_creacion: string
  fecha_vencimiento: string | null
  etiquetas: string[]
  asignados: string[]
  tipo: TipoTarea | null
  oportunidad: Oportunidad | null
}

/** Elemento de un catálogo compartido (`GET /etiquetas`, `GET /personas`). */
export interface ElementoCatalogo {
  id: number
  nombre: string
}
