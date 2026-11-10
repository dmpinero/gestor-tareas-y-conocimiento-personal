import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h } from 'vue'

import { useAhora } from '../useAhora'

const INICIO = new Date(2026, 10, 9, 18, 45, 30)

// Componente mínimo que pinta la hora compartida en milisegundos.
const COMPONENTE_RELOJ = defineComponent({
  setup() {
    const { ahora } = useAhora()
    return () => h('span', String(ahora.value.getTime()))
  },
})

describe('useAhora', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(INICIO)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('comparte un único intervalo entre todos los componentes suscritos', () => {
    const espiaIntervalo = vi.spyOn(globalThis, 'setInterval')

    const primero = mount(COMPONENTE_RELOJ)
    const segundo = mount(COMPONENTE_RELOJ)
    const tercero = mount(COMPONENTE_RELOJ)

    expect(espiaIntervalo).toHaveBeenCalledTimes(1)
    expect(vi.getTimerCount()).toBe(1)
    primero.unmount()
    segundo.unmount()
    tercero.unmount()
  })

  it('detiene el intervalo solo cuando se desmonta el último componente', () => {
    const primero = mount(COMPONENTE_RELOJ)
    const segundo = mount(COMPONENTE_RELOJ)

    primero.unmount()
    expect(vi.getTimerCount()).toBe(1)
    segundo.unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('actualiza la hora cada segundo en todos los suscriptores', async () => {
    const primero = mount(COMPONENTE_RELOJ)
    const segundo = mount(COMPONENTE_RELOJ)
    expect(primero.text()).toBe(String(INICIO.getTime()))

    vi.advanceTimersByTime(1000)
    await primero.vm.$nextTick()

    expect(primero.text()).toBe(String(INICIO.getTime() + 1000))
    expect(segundo.text()).toBe(String(INICIO.getTime() + 1000))
    primero.unmount()
    segundo.unmount()
  })

  it('al volver a suscribirse tras quedarse sin suscriptores parte de la hora actual', () => {
    mount(COMPONENTE_RELOJ).unmount()
    vi.setSystemTime(new Date(INICIO.getTime() + 60_000))

    const reloj = mount(COMPONENTE_RELOJ)

    expect(reloj.text()).toBe(String(INICIO.getTime() + 60_000))
    expect(vi.getTimerCount()).toBe(1)
    reloj.unmount()
  })
})
