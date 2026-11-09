/** Tarea tal como la devuelve la API (`GET`/`POST /tareas`, `PUT /tareas/{id}`). */
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
}

/**
 * Cuerpo de `POST /tareas` y `PUT /tareas/{id}`. La prioridad va de 1 (más
 * prioritaria) a 5; las fechas son ISO 8601 sin zona horaria. Las etiquetas y
 * personas que no existan se crean al guardar.
 */
export interface DatosTarea {
  nombre: string
  prioridad: number | null
  descripcion: string
  fecha_creacion: string
  fecha_vencimiento: string | null
  etiquetas: string[]
  asignados: string[]
}

/** Elemento de un catálogo compartido (`GET /etiquetas`, `GET /personas`). */
export interface ElementoCatalogo {
  id: number
  nombre: string
}
