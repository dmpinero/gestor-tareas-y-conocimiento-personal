import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// useModoOscuro lee matchMedia al cargarse el módulo, y jsdom no lo implementa:
// hay que definirlo antes de que se evalúen los imports estáticos de abajo.
vi.hoisted(() => {
  window.matchMedia = ((consulta: string) => ({
    matches: false,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  })) as unknown as typeof window.matchMedia
})

import { useModoOscuro } from '@/composables/useModoOscuro'
import ConmutadorTema from '../ConmutadorTema.vue'

beforeEach(async () => {
  localStorage.clear()
  useModoOscuro().temaActual.value = 'claro'
  await nextTick()
})

describe('ConmutadorTema', () => {
  it('en modo claro es un switch no marcado que ofrece cambiar a modo oscuro', () => {
    const wrapper = mount(ConmutadorTema)

    const boton = wrapper.get('[role="switch"]')
    expect(boton.attributes('aria-checked')).toBe('false')
    expect(boton.attributes('aria-label')).toBe('Cambiar a modo oscuro')
  })

  it('al pulsarlo activa el modo oscuro, lo persiste y actualiza su etiqueta', async () => {
    const wrapper = mount(ConmutadorTema)

    await wrapper.get('[role="switch"]').trigger('click')

    const boton = wrapper.get('[role="switch"]')
    expect(boton.attributes('aria-checked')).toBe('true')
    expect(boton.attributes('aria-label')).toBe('Cambiar a modo claro')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('tema-preferido')).toBe('oscuro')
  })
})
