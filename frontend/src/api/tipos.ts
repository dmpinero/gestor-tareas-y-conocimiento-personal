/** Tarea tal como la devuelve la API (`GET`/`POST /tareas`). */
export interface Tarea {
  id: number
  nombre: string
  prioridad: number | null
  descripcion: string
}

/** Cuerpo de `POST /tareas`. La prioridad va de 1 (más prioritaria) a 5. */
export interface DatosTarea {
  nombre: string
  prioridad: number | null
  descripcion: string
}
