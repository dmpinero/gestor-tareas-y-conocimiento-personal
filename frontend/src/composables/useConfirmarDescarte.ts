import { inject, onBeforeUnmount, provide, ref, type InjectionKey, type Ref } from 'vue'

/**
 * Evita perder datos al cerrar algo con cambios sin guardar (una modal con un
 * formulario, una edición en línea…). `pedirCierre(cerrar)` cierra en el acto
 * si `hayCambios()` es falso; si no, abre la confirmación de descarte
 * (`confirmando`) y solo ejecuta `cerrar` al pulsar "Descartar". "Seguir
 * editando" (o Escape en la confirmación) la cierra sin tocar nada y devuelve
 * el foco al elemento que lo tenía o, si era el `<body>` (p. ej. tras un clic
 * en el fondo), a la modal abierta.
 *
 * Se conecta con `DialogoDescartarCambios`: `:abierto="confirmando"`,
 * `@descartar="descartar"`, `@update:abierto="alCambiarConfirmacion"` y
 * `@cierre-foco="alDevolverFoco"`.
 */
export interface ConfirmacionDescarte {
  confirmando: Ref<boolean>
  pedirCierre: (cerrar: () => void) => void
  descartar: () => void
  alCambiarConfirmacion: (abierto: boolean) => void
  alDevolverFoco: (evento: Event) => void
}

export function useConfirmarDescarte(hayCambios: () => boolean): ConfirmacionDescarte {
  const confirmando = ref(false)
  let cierrePendiente: (() => void) | null = null
  let focoPrevio: HTMLElement | null = null
  let descartado = false

  function pedirCierre(cerrar: () => void): void {
    if (confirmando.value) return
    if (!hayCambios()) {
      cerrar()
      return
    }
    cierrePendiente = cerrar
    descartado = false
    focoPrevio = document.activeElement instanceof HTMLElement ? document.activeElement : null
    confirmando.value = true
  }

  function descartar(): void {
    const cerrar = cierrePendiente
    cierrePendiente = null
    descartado = true
    confirmando.value = false
    cerrar?.()
  }

  function alCambiarConfirmacion(abierto: boolean): void {
    if (abierto) return
    cierrePendiente = null
    confirmando.value = false
  }

  // Al descartar, el foco lo coloca quien cierra (p. ej. la modal al cerrarse
  // lo devuelve a su disparador). Al seguir editando, vuelve al formulario.
  function alDevolverFoco(evento: Event): void {
    const previo = focoPrevio
    focoPrevio = null
    if (descartado) return
    evento.preventDefault()
    if (previo && previo.isConnected && previo !== document.body) {
      previo.focus()
      return
    }
    document.querySelector<HTMLElement>('[role="dialog"]')?.focus()
  }

  return { confirmando, pedirCierre, descartar, alCambiarConfirmacion, alDevolverFoco }
}

// --- Borradores de los componentes que hay dentro de una modal -------------
// Una modal (p. ej. el detalle de una tarea) proporciona un registro; los
// componentes que contiene (comentarios, subtareas…) registran una función que
// dice si tienen algo escrito sin guardar. Fuera de una modal que lo
// proporcione, registrar no hace nada.

type HayBorrador = () => boolean

const CLAVE_BORRADORES: InjectionKey<Set<HayBorrador>> = Symbol('borradores')

/** Crea el registro de borradores para los descendientes y dice si hay alguno. */
export function proveerBorradores(): () => boolean {
  const registro = new Set<HayBorrador>()
  provide(CLAVE_BORRADORES, registro)
  return () => [...registro].some((hayBorrador) => hayBorrador())
}

/** Registra un borrador del componente mientras está montado. */
export function registrarBorrador(hayBorrador: HayBorrador): void {
  const registro = inject(CLAVE_BORRADORES, null)
  if (registro === null) return
  registro.add(hayBorrador)
  onBeforeUnmount(() => registro.delete(hayBorrador))
}
