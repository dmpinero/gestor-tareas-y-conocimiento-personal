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
