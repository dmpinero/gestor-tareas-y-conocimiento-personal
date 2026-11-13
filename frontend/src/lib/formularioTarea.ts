import type { TipoTarea } from '@/api/tipos'

/**
 * Valores del formulario de alta y edición de una tarea, tal como los escribe
 * el usuario. La prioridad llega como número desde un `<input type="number">`,
 * o como cadena vacía cuando el campo se deja en blanco; las fechas, como texto
 * `dd/mm/aaaa hh:mm:ss`. El tipo vacío es "Sin tipo"; los campos de la
 * oportunidad solo se envían si el tipo es "Oportunidad". El grupo de estados
 * vacío es "Sin grupo"; si no, es el id del grupo. Igual con el workflow:
 * vacío es "Sin workflow".
 */
export interface ValoresFormularioTarea {
  nombre: string
  prioridad: string | number | null
  descripcion: string
  fechaCreacion: string
  fechaVencimiento: string
  etiquetas: string[]
  asignados: string[]
  tipo: TipoTarea | ''
  oportunidad: { codigo: string; descripcion: string; observaciones: string }
  grupoEstadosId: number | ''
  workflowId: number | ''
}
