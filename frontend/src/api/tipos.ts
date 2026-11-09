/** Tarea tal como la devuelve la API (`GET`/`POST /tareas`, `PUT /tareas/{id}`). */
export interface Tarea {
  id: number
  nombre: string
  prioridad: number | null
  descripcion: string
  /** ISO 8601 sin zona horaria (`YYYY-MM-DDTHH:MM:SS`), en hora local. */
  fecha_hora: string
}

/**
 * Cuerpo de `POST /tareas` y `PUT /tareas/{id}`. La prioridad va de 1 (más
 * prioritaria) a 5; `fecha_hora` es ISO 8601 sin zona horaria.
 */
export interface DatosTarea {
  nombre: string
  prioridad: number | null
  descripcion: string
  fecha_hora: string
}
