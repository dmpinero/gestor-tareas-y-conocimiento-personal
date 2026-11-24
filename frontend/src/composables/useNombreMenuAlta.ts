import { onMounted, ref, type Ref } from 'vue'

import { obtenerConfiguracionAlta, obtenerConfiguracionAxasMs3 } from '@/api/altaOportunidades'

/** Nombre de la entrada del alta si no se puede leer la configuración local. */
export const NOMBRE_MENU_ALTA_PREDETERMINADO = 'Alta de oportunidades'
/** Igual, para el alta AXAS MS3. */
export const NOMBRE_MENU_AXAS_MS3_PREDETERMINADO = 'Oportunidades AXAS MS3'

// El nombre de la entrada del menú del alta viene de la configuración local
// (fuera del repositorio), porque puede incluir datos del cliente. Si el
// servicio no responde se usa el predeterminado.
function useNombreMenu(
  predeterminado: string,
  obtener: () => Promise<{ nombre_menu: string }>,
): Ref<string> {
  const nombre = ref(predeterminado)
  onMounted(async () => {
    try {
      nombre.value = (await obtener()).nombre_menu
    } catch {
      // Se queda el predeterminado.
    }
  })
  return nombre
}

export function useNombreMenuAlta(): Ref<string> {
  return useNombreMenu(NOMBRE_MENU_ALTA_PREDETERMINADO, obtenerConfiguracionAlta)
}

export function useNombreMenuAltaAxasMs3(): Ref<string> {
  return useNombreMenu(NOMBRE_MENU_AXAS_MS3_PREDETERMINADO, obtenerConfiguracionAxasMs3)
}
