import { onMounted, ref, type Ref } from 'vue'

import { obtenerConfiguracionAlta } from '@/api/altaOportunidades'

/** Nombre de la entrada del alta si no se puede leer la configuración local. */
export const NOMBRE_MENU_ALTA_PREDETERMINADO = 'Alta de oportunidades'

// El nombre de la entrada del menú del alta viene de la configuración local
// (fuera del repositorio), porque puede incluir datos del cliente. Si el
// servicio no responde se usa el predeterminado.
export function useNombreMenuAlta(): Ref<string> {
  const nombre = ref(NOMBRE_MENU_ALTA_PREDETERMINADO)
  onMounted(async () => {
    try {
      nombre.value = (await obtenerConfiguracionAlta()).nombre_menu
    } catch {
      // Se queda el predeterminado.
    }
  })
  return nombre
}
