import { type InjectionKey, type Ref, inject, provide } from 'vue'

export const ANCHO_PANEL = '16rem'
export const ANCHO_PANEL_ICONO = '3rem'
export const CLAVE_ALMACENAMIENTO = 'panel-lateral-colapsado'

export interface EstadoPanelLateral {
  estado: Ref<'expandido' | 'colapsado'>
  abiertoEnMovil: Ref<boolean>
  esMovil: Ref<boolean>
  alternar: () => void
}

export const claveInyeccionPanelLateral = Symbol(
  'panel-lateral',
) as InjectionKey<EstadoPanelLateral>

export function proveerPanelLateral(estado: EstadoPanelLateral): void {
  provide(claveInyeccionPanelLateral, estado)
}

export function useSidebar(): EstadoPanelLateral {
  const contexto = inject(claveInyeccionPanelLateral)
  if (!contexto) {
    throw new Error('useSidebar debe usarse dentro de un SidebarProvider')
  }
  return contexto
}
