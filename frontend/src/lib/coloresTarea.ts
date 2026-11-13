// Colores con los que la tabla de tareas distingue prioridades, grupos y
// estados. Las clases son literales completos para que Tailwind las genere.

/** Clave de una prioridad para los colores: 1–5 o `'sin'` (sin prioridad). */
export type ClavePrioridad = 1 | 2 | 3 | 4 | 5 | 'sin'

export const CLAVES_PRIORIDAD: readonly ClavePrioridad[] = [1, 2, 3, 4, 5, 'sin']

export function clavePrioridad(prioridad: number | null): ClavePrioridad {
  return prioridad !== null && Number.isInteger(prioridad) && prioridad >= 1 && prioridad <= 5
    ? (prioridad as ClavePrioridad)
    : 'sin'
}

// Relleno de cada prioridad en la barra de distribución: 1 rojo, 2 naranja,
// 3 azul, 4 verde azulado y 5 gris; sin prioridad, el tono apagado del tema.
export const RELLENO_PRIORIDAD: Record<ClavePrioridad, string> = {
  1: 'bg-red-600 dark:bg-red-500',
  2: 'bg-orange-500 dark:bg-orange-400',
  3: 'bg-blue-600 dark:bg-blue-400',
  4: 'bg-teal-600 dark:bg-teal-400',
  5: 'bg-gray-500 dark:bg-gray-400',
  sin: 'bg-muted-foreground/30',
}

// Píldoras de texto: fondo claro con texto oscuro y, en modo oscuro, fondo
// oscuro con texto claro, con un contraste por encima de 4,5:1 (WCAG AA).
export const PILDORA_PRIORIDAD: Record<Exclude<ClavePrioridad, 'sin'>, string> = {
  1: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200',
  2: 'bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-200',
  3: 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200',
  4: 'bg-teal-100 text-teal-800 dark:bg-teal-950 dark:text-teal-200',
  5: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100',
}

export const PILDORA_TIPO = 'bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-200'

const PILDORA_ESTADO_INICIAL = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-100'
const PILDORA_ESTADO_INTERMEDIO = 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200'
const PILDORA_ESTADO_FINAL =
  'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200'

/**
 * Color del estado de una tarea según su posición en el grupo: el primero
 * (o un estado que no se encuentra) gris, el último verde y los demás azules.
 */
export function pildoraEstado(indice: number, total: number): string {
  if (indice <= 0 || total <= 1) return PILDORA_ESTADO_INICIAL
  return indice === total - 1 ? PILDORA_ESTADO_FINAL : PILDORA_ESTADO_INTERMEDIO
}

export const CLASE_PILDORA =
  'inline-flex max-w-full items-center rounded-full px-2 py-0.5 text-xs font-medium'
