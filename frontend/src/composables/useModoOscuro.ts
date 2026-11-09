import { ref, watchEffect } from 'vue'

type Tema = 'claro' | 'oscuro'

const CLAVE_ALMACENAMIENTO = 'tema-preferido'

function obtenerTemaInicial(): Tema {
  const guardado = localStorage.getItem(CLAVE_ALMACENAMIENTO)
  if (guardado === 'claro' || guardado === 'oscuro') return guardado
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'oscuro' : 'claro'
}

const temaActual = ref<Tema>(obtenerTemaInicial())

watchEffect(() => {
  document.documentElement.classList.toggle('dark', temaActual.value === 'oscuro')
})

export function useModoOscuro() {
  function alternar(): void {
    temaActual.value = temaActual.value === 'oscuro' ? 'claro' : 'oscuro'
    localStorage.setItem(CLAVE_ALMACENAMIENTO, temaActual.value)
  }

  return { temaActual, alternar }
}
