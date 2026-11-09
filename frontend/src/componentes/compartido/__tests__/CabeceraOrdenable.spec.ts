import { ChevronDown, ChevronUp, ChevronsUpDown, Hash } from '@lucide/vue'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CabeceraOrdenable from '../CabeceraOrdenable.vue'

describe('CabeceraOrdenable', () => {
  it('es un botón cuyo nombre accesible es la etiqueta de la columna', () => {
    const wrapper = mount(CabeceraOrdenable, {
      props: { activo: false, direccion: 'asc' },
      slots: { default: 'Nombre' },
    })

    const boton = wrapper.get('button')
    expect(boton.attributes('type')).toBe('button')
    expect(boton.text()).toBe('Nombre')
    expect(boton.attributes('aria-label')).toBeUndefined()
    for (const icono of boton.findAll('svg')) {
      expect(icono.attributes('aria-hidden')).toBe('true')
    }
  })

  it('emite "ordenar" al pulsar', async () => {
    const wrapper = mount(CabeceraOrdenable, {
      props: { activo: false, direccion: 'asc' },
      slots: { default: 'Nombre' },
    })

    await wrapper.get('button').trigger('click')

    expect(wrapper.emitted('ordenar')).toHaveLength(1)
  })

  it('sin icono de columna solo muestra el icono de orden', () => {
    const wrapper = mount(CabeceraOrdenable, { props: { activo: false, direccion: 'asc' } })

    expect(wrapper.findAll('svg')).toHaveLength(1)
  })

  it('con icono de columna lo muestra con su color', () => {
    const wrapper = mount(CabeceraOrdenable, {
      props: { icono: Hash, colorIcono: 'text-blue-500', activo: false, direccion: 'asc' },
    })

    expect(wrapper.findAll('svg')).toHaveLength(2)
    expect(wrapper.findComponent(Hash).classes()).toContain('text-blue-500')
  })

  it('cuando no está activa muestra el icono de orden neutro', () => {
    const wrapper = mount(CabeceraOrdenable, { props: { activo: false, direccion: 'desc' } })

    expect(wrapper.findComponent(ChevronsUpDown).exists()).toBe(true)
    expect(wrapper.findComponent(ChevronUp).exists()).toBe(false)
    expect(wrapper.findComponent(ChevronDown).exists()).toBe(false)
  })

  it('activa en ascendente muestra la flecha hacia arriba', () => {
    const wrapper = mount(CabeceraOrdenable, { props: { activo: true, direccion: 'asc' } })

    expect(wrapper.findComponent(ChevronUp).exists()).toBe(true)
    expect(wrapper.findComponent(ChevronsUpDown).exists()).toBe(false)
  })

  it('activa en descendente muestra la flecha hacia abajo', () => {
    const wrapper = mount(CabeceraOrdenable, { props: { activo: true, direccion: 'desc' } })

    expect(wrapper.findComponent(ChevronDown).exists()).toBe(true)
    expect(wrapper.findComponent(ChevronsUpDown).exists()).toBe(false)
  })
})
