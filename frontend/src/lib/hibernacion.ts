import type { Tarea } from '@/api/tipos'

// `hibernada_desde` es opcional aquí para aceptar tareas de una API anterior
// que todavía no lo mande.
type DatosCongelacion = Pick<Tarea, 'congelada_en'> & Partial<Pick<Tarea, 'hibernada_desde'>>

/** `true` si la tarea está hibernada (su reloj está parado hasta reanudarla). */
export function estaHibernada(tarea: Partial<Pick<Tarea, 'hibernada_desde'>>): boolean {
  return (tarea.hibernada_desde ?? null) !== null
}

/**
 * Instante (UTC, "YYYY-MM-DDTHH:MM:SSZ") en el que se congela la cuenta atrás
 * de la tarea, o `null` si sigue contando. La congelan tanto estar completada
 * o en DONE (`congelada_en`) como estar hibernada (`hibernada_desde`); si se
 * dan las dos, cuenta la más antigua, que es cuando el reloj dejó de avanzar.
 * Es lo que reciben los componentes de vencimiento en `congeladaEn`.
 */
export function instanteCongelado(tarea: DatosCongelacion): string | null {
  const congelada = tarea.congelada_en ?? null
  const hibernada = tarea.hibernada_desde ?? null
  if (congelada === null) return hibernada
  if (hibernada === null) return congelada
  return new Date(hibernada).getTime() < new Date(congelada).getTime() ? hibernada : congelada
}
