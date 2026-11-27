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
 * Subtarea de una tarea. Solo existe dentro de su tarea: se crea con
 * `POST /tareas/{id}/subtareas`, se edita con
 * `PUT /tareas/{id}/subtareas/{id_subtarea}`, cambia de estado con
 * `PATCH /tareas/{id}/subtareas/{id_subtarea}/resuelta` y se borra con
 * `DELETE /tareas/{id}/subtareas/{id_subtarea}`; todas devuelven la tarea
 * completa. Al asignar un workflow a la tarea (en el alta, o en la edición si
 * cambia), cada uno de sus pasos se copia como una subtarea. Sus comentarios se gestionan en
 * `/tareas/{id}/subtareas/{id_subtarea}/comentarios`, igual que los de la tarea.
 */
export interface Subtarea {
  id: number
  /** Entre 1 y 200 caracteres, sin espacios al principio ni al final. */
  nombre: string
  /** Nombre de la persona asignada (del catálogo de personas); `null` si no
   * tiene. */
  asignado: string | null
  /** De 1 (más prioritaria) a 5; `null` si no tiene. */
  prioridad: number | null
  resuelta: boolean
  /** Número de comentarios de la subtarea. */
  comentarios: number
}

/** Cuerpo de `POST /tareas/{id}/subtareas`. Si `asignado` no existe en el
 * catálogo de personas, se crea al guardar. */
export interface DatosSubtarea {
  nombre: string
  asignado?: string
  prioridad?: number
}

/** Cuerpo de `PUT /tareas/{id}/subtareas/{id_subtarea}`. Es un reemplazo
 * completo: `asignado` o `prioridad` a `null` los vacían. Como en el alta, si
 * `asignado` no existe en el catálogo de personas, se crea al guardar. */
export interface DatosEdicionSubtarea {
  nombre: string
  asignado: string | null
  prioridad: number | null
}

/**
 * Tarea tal como la devuelve la API (`GET`/`POST /tareas`, `PUT /tareas/{id}`,
 * `PATCH /tareas/{id}/completada`). Se borra con `DELETE /tareas/{id}` (204),
 * que borra también sus subtareas y todos los comentarios.
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
  /** Subtareas en el orden de la API: primero las de los pasos del workflow de la
   * tarea, en el orden de esos pasos, y después las demás por orden de alta; vacía
   * si no tiene. */
  subtareas: Subtarea[]
  /** Grupo de estados al que apunta la tarea; `null` si no tiene. */
  grupo_estados: ReferenciaNombre | null
  /** Estado actual dentro de su grupo; `null` si no tiene grupo. Solo cambia
   * con `PATCH /tareas/{id}/estado` o al cambiar de grupo (va al primero). */
  estado: ReferenciaNombre | null
  /** Workflow de la tarea; `null` si no tiene. */
  workflow: ReferenciaNombre | null
  /** Nombre del subestado de la tarea (del catálogo `/subestados`, como mucho
   * uno); `null` si no tiene. */
  subestado: string | null
  /** Instante en UTC (`YYYY-MM-DDTHH:MM:SSZ`) desde el que el contador de
   * vencimiento está congelado, o `null` si no lo está. Lo pone el servidor: la
   * tarea está congelada mientras está completada o en un estado llamado DONE, y
   * el contador muestra lo que faltaba para `fecha_vencimiento` en ese instante. */
  congelada_en: string | null
  /** Instante en UTC (`YYYY-MM-DDTHH:MM:SSZ`) desde el que la tarea está
   * hibernada, o `null` si no lo está. Cambia con `POST /tareas/{id}/hibernar` y
   * `POST /tareas/{id}/reanudar`; mientras dura, el contador de vencimiento está
   * parado y, al reanudar, `fecha_vencimiento` se retrasa lo que duró. Es
   * independiente de `congelada_en`. */
  hibernada_desde: string | null
  /** Ids de las tareas vinculadas ("Tareas relacionadas" en el detalle), en
   * orden ascendente. La relación es simétrica: si A tiene a B, B tiene a A.
   * Cambia con `POST /tareas/{id}/vinculadas` (`{ ids }`) y
   * `DELETE /tareas/{id}/vinculadas/{vinculada_id}`, que devuelven solo la
   * tarea {id}; al borrar una tarea desaparecen sus vínculos. */
  vinculadas: number[]
}

/** Cuerpo de `POST /tareas/{id}/vinculadas`: ids de las tareas que se vinculan
 * con {id} (al menos uno, sin {id}); los ya vinculados se ignoran. */
export interface DatosVinculacion {
  ids: number[]
}

/** Cuerpo de `POST /tareas/{id}/hibernar`. Con `comentario` (HTML, con las
 * mismas reglas que los comentarios de la tarea) la API lo añade como un
 * comentario más de la tarea; `null` hiberna sin comentario. */
export interface DatosHibernacion {
  comentario: string | null
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
  /** Grupo de estados de la tarea, o `null` sin grupo. Al asignarlo o
   * cambiarlo, la tarea pasa al primer estado del grupo. */
  grupo_estados_id: number | null
  /** Workflow de la tarea, o `null` sin workflow. Al asignarlo en el alta, o
   * al cambiarlo en la edición, sus pasos se añaden como subtareas nuevas. */
  workflow_id: number | null
  /** Nombre del subestado, o `null` sin subestado. Si no existe en el catálogo
   * de subestados, se crea al guardar. En la edición, si falta, la tarea
   * conserva el suyo. */
  subestado?: string | null
}

/** Elemento de un catálogo compartido (`GET /etiquetas`, `GET /personas`,
 * `GET /subestados`). Los subestados también se crean, renombran y eliminan en
 * Ajustes (`POST /subestados`, `PUT`/`DELETE /subestados/{id}`). */
export interface ElementoCatalogo {
  id: number
  nombre: string
}

/** Código de servicio del catálogo del alta de oportunidades AXAS MS3 (p. ej.
 * «AXAS0024»): `GET /codigos-servicio`, `POST /codigos-servicio` y
 * `PUT`/`DELETE /codigos-servicio/{id}`. El nombre tiene de 2 a 20 caracteres, sin
 * espacios, y es único sin distinguir mayúsculas (409 si se repite). */
export type CodigoServicio = ElementoCatalogo

/**
 * Paso de un workflow. `numero` es la posición 1..n que asigna el sistema; un
 * paso nuevo va al final y al reordenar se recalcula.
 */
export interface PasoWorkflow {
  id: number
  numero: number
  /** Entre 1 y 50 caracteres, sin espacios al principio ni al final. */
  nombre: string
  /** Número de comentarios del paso. Se gestionan en
   * `/workflows/{id}/pasos/{id_paso}/comentarios`, igual que los de las
   * subtareas, y se copian a cada subtarea que nace del paso. */
  comentarios: number
}

/**
 * Workflow de Ajustes (`/workflows`): pasos que se realizan en orden y que se
 * copian como subtareas en las tareas que lo usan. Las acciones sobre sus pasos
 * (`/workflows/{id}/pasos`, `/workflows/{id}/orden`) devuelven el workflow
 * completo.
 */
export interface Workflow {
  id: number
  /** Entre 1 y 50 caracteres, único entre los workflows sin distinguir
   * mayúsculas. */
  nombre: string
  /** Por número. */
  pasos: PasoWorkflow[]
}

/** Subtarea vinculada a un paso cuyo nombre ya no es el del paso. */
export interface RenombreSubtarea {
  /** Id de la subtarea. */
  id: number
  nombre_actual: string
  /** Nombre actual del paso. */
  nombre_nuevo: string
}

/** Cambios de una tarea al sincronizarla con su workflow. */
export interface CambiosDeTarea {
  /** Id de la tarea. */
  id: number
  nombre: string
  /** Nombres de los pasos sin subtarea vinculada, por número. */
  subtareas_a_anadir: string[]
  subtareas_a_renombrar: RenombreSubtarea[]
}

/**
 * Respuesta de `GET /workflows/{id}/sincronizacion` (cambios pendientes, sin
 * modificar nada) y de `POST /workflows/{id}/sincronizacion` (cambios
 * aplicados). Solo incluye las tareas no completadas del workflow que cambian.
 */
export interface CambiosDeLasTareas {
  tareas: CambiosDeTarea[]
}

/** Referencia a otro recurso por su id y su nombre. */
export interface ReferenciaNombre {
  id: number
  nombre: string
}

/** Estado de un grupo de estados. `posicion` (1..n) solo define el orden de
 * las columnas del tablero; se puede pasar de cualquier estado a cualquier otro. */
export interface EstadoGrupo {
  id: number
  /** Entre 1 y 50 caracteres, único dentro de su grupo. */
  nombre: string
  posicion: number
  /** Número de tareas en este estado. */
  tareas: number
}

/**
 * Grupo de estados (`/grupos-estados`). Las tareas apuntan al grupo: los
 * cambios en sus estados se reflejan en ellas. Las acciones sobre sus estados
 * (`/grupos-estados/{id}/estados`, `/grupos-estados/{id}/orden`) devuelven el
 * grupo completo.
 */
export interface GrupoEstados {
  id: number
  /** Entre 1 y 50 caracteres, único entre los grupos. */
  nombre: string
  /** Número de tareas del grupo. */
  tareas: number
  estados: EstadoGrupo[]
}

/**
 * Tarea o subtarea en la que se está trabajando ahora (`/foco`). Solo hay
 * una a la vez: `PUT /foco` sustituye la anterior sin avisar y devuelve este
 * mismo objeto; `GET /foco` devuelve `null` si no hay ninguna y
 * `DELETE /foco` (204) la quita. Borrar la tarea o subtarea en foco también
 * la quita.
 */
export interface Foco {
  tarea_id: number
  tarea_nombre: string
  /** `null` si el foco es la tarea entera. */
  subtarea_id: number | null
  subtarea_nombre: string | null
  /** ISO 8601: instante desde el que se trabaja en ella (se reinicia en cada `PUT`). */
  desde: string
}

/** Una entrada de la cola de siguientes ("A continuación") o de las
 * sugerencias elegidas: una tarea entera (`subtarea_id` `null`) o una subtarea
 * suya, con sus nombres actuales. Se identifica por (`tarea_id`,
 * `subtarea_id`). `GET /siguientes` la devuelve en el orden de la cola y sin
 * las tareas completadas ni las subtareas resueltas (siguen en la cola: si
 * vuelven a estar pendientes, vuelven a su sitio). `POST /siguientes`
 * (`{ tarea_id, subtarea_id? }`) la añade al final, `PUT /siguientes`
 * (`{ entradas }`) reordena la cola visible y `DELETE /siguientes/{tarea_id}`
 * (con `?subtarea_id=` para una subtarea) la quita; todas devuelven la cola
 * completa. Poner en foco una subtarea saca su entrada y la de su tarea; una
 * tarea entera, solo la de la tarea. Borrarlas las saca. */
export interface TareaSiguiente {
  tarea_id: number
  tarea_nombre: string
  subtarea_id: number | null
  subtarea_nombre: string | null
}

/** Lo que identifica una entrada de siguientes o de sugerencias elegidas. */
export interface ClaveEntradaSiguiente {
  tarea_id: number
  subtarea_id: number | null
}

/** Cuerpo de `PUT /foco`. */
export interface DatosFoco {
  tarea_id: number
  subtarea_id: number | null
}

/** Un periodo de foco de `GET /foco/historial`. Los nombres son los actuales si
 * la tarea o subtarea sigue existiendo; si se borró, su id es `null` y queda el
 * último nombre conocido. */
export interface EntradaHistorialFoco {
  id: number
  tarea_id: number | null
  tarea_nombre: string
  subtarea_id: number | null
  subtarea_nombre: string | null
  /** ISO 8601 con zona: cuándo se fijó el foco. */
  desde: string
  /** ISO 8601 con zona, o `null` si es el foco actual (en curso). */
  hasta: string | null
}

/** `GET /conocimiento/estado`: si están las credenciales en el backend y qué hay
 * en el índice local de Notion. */
export interface EstadoConocimiento {
  configurado: { notion: boolean; anthropic: boolean }
  paginas: number
  fragmentos: number
  /** Instante en UTC (`YYYY-MM-DDTHH:MM:SSZ`) de la última sincronización, o
   * `null` si nunca se ha sincronizado. */
  ultima_sincronizacion: string | null
}

/** `POST /conocimiento/sincronizar`: el índice tras sincronizar y qué cambió. */
export interface ResultadoSincronizacion {
  paginas: number
  fragmentos: number
  nuevas: number
  actualizadas: number
  eliminadas: number
  /** Instante en UTC (`YYYY-MM-DDTHH:MM:SSZ`). */
  ultima_sincronizacion: string
}

/** Una página de Notion citada por una respuesta (evento SSE `fuentes`). */
export interface FuenteConocimiento {
  pagina_id: string
  titulo: string
  url: string
}

/** Un trozo de una página de Notion que coincide con `GET /conocimiento/buscar`. */
export interface ResultadoBusquedaConocimiento {
  pagina_id: string
  titulo: string
  url: string
  fragmento: string
  /** Posición del trozo dentro de su página (0 el primero). */
  orden: number
}

export type RolMensajeConocimiento = 'usuario' | 'asistente'

/** Un mensaje del historial que se envía a `POST /conocimiento/preguntar`. */
export interface MensajeConocimiento {
  rol: RolMensajeConocimiento
  texto: string
}
