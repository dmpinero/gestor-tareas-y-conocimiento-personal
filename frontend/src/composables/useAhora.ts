import { getCurrentScope, onScopeDispose, readonly, ref, type Ref } from 'vue'

// Reloj compartido: un único intervalo para todos los componentes que lo usan,
// aunque la tabla tenga cientos de filas con cuenta atrás.
const INTERVALO_MS = 1000

const ahora = ref(new Date())
let suscriptores = 0
let intervalo: ReturnType<typeof setInterval> | null = null

function iniciar(): void {
  // Tras un tiempo sin suscriptores la hora guardada está desfasada.
  ahora.value = new Date()
  intervalo = setInterval(() => {
    ahora.value = new Date()
  }, INTERVALO_MS)
}

function detener(): void {
  if (intervalo !== null) clearInterval(intervalo)
  intervalo = null
}

/**
 * Devuelve la hora actual como un `Date` reactivo que se actualiza cada
 * segundo. El intervalo arranca con el primer suscriptor y se detiene cuando
 * se desmonta el último.
 */
export function useAhora(): { ahora: Readonly<Ref<Date>> } {
  suscriptores += 1
  if (suscriptores === 1) iniciar()

  if (getCurrentScope()) {
    onScopeDispose(() => {
      suscriptores -= 1
      if (suscriptores === 0) detener()
    })
  }

  return { ahora: readonly(ahora) as Readonly<Ref<Date>> }
}
