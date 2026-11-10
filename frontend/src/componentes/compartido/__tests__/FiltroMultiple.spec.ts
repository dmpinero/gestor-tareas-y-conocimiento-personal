import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import FiltroMultiple from '../FiltroMultiple.vue'

const items = [
  { id: 1, nombre: 'Opción A' },
  { id: 2, nombre: 'Opción B' },
]

const propsBase = {
  items,
  idBase: 'filtro-test',
  etiquetaBoton: 'Filtrar por opción',
  nombreSingular: 'opción',
  nombrePlural: 'opciones',
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('FiltroMultiple', () => {
  // Regresión (WCAG 2.5.3, axe `label-content-name-mismatch`): el nombre accesible
  // del botón debe contener su texto visible.
  it('el nombre accesible del botón incluye su texto visible', () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1] },
    })

    const boton = wrapper.get('button')
    expect(boton.attributes('aria-label')).toBe(`Filtrar por opción: ${boton.text()}`)
  })

  it('con todos los elementos seleccionados muestra "Todas las elementos"', () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1, 2] },
    })

    expect(wrapper.text()).toContain('Todas las opciones')
  })

  it('con un elemento seleccionado muestra su nombre', () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1] },
    })

    expect(wrapper.text()).toContain('Opción A')
  })

  it('con varios elementos seleccionados (sin ser todos) muestra el recuento', () => {
    const wrapper = mount(FiltroMultiple, {
      props: {
        ...propsBase,
        items: [...items, { id: 3, nombre: 'Opción C' }],
        modelValue: [1, 2],
      },
    })

    expect(wrapper.text()).toContain('2 opciones')
  })

  it('con ningún elemento seleccionado muestra "Ninguna opción"', () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [] },
    })

    expect(wrapper.text()).toContain('Ninguna opción')
  })

  it('marcar un elemento individual emite el modelo actualizado', async () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1] },
      attachTo: document.body,
    })

    await wrapper.get('button').trigger('click')
    const casillaB = document.body.querySelector<HTMLElement>('#filtro-test-1')
    casillaB?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([[[1, 2]]])
    wrapper.unmount()
  })

  it('desmarcar un elemento individual lo quita del modelo', async () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1, 2] },
      attachTo: document.body,
    })

    await wrapper.get('button').trigger('click')
    const casillaA = document.body.querySelector<HTMLElement>('#filtro-test-0')
    casillaA?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([[[2]]])
    wrapper.unmount()
  })

  it('"Seleccionar todas" marca todos los elementos de golpe', async () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [] },
      attachTo: document.body,
    })

    await wrapper.get('button').trigger('click')
    const casillaTodos = document.body.querySelector<HTMLElement>('#filtro-test-todos')
    casillaTodos?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([[[1, 2]]])
    wrapper.unmount()
  })

  it('desmarcar "Seleccionar todas" cuando están todos marcados los vacía', async () => {
    const wrapper = mount(FiltroMultiple, {
      props: { ...propsBase, modelValue: [1, 2] },
      attachTo: document.body,
    })

    await wrapper.get('button').trigger('click')
    const casillaTodos = document.body.querySelector<HTMLElement>('#filtro-test-todos')
    casillaTodos?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([[[]]])
    wrapper.unmount()
  })

  it('acepta identificadores de texto y asocia cada casilla a su etiqueta por posición', async () => {
    const wrapper = mount(FiltroMultiple, {
      props: {
        ...propsBase,
        items: [
          { id: 'Mi etiqueta', nombre: 'Mi etiqueta' },
          { id: '', nombre: 'Sin etiquetas' },
        ],
        modelValue: ['Mi etiqueta'],
      },
      attachTo: document.body,
    })

    expect(wrapper.text()).toContain('Mi etiqueta')
    await wrapper.get('button').trigger('click')
    const etiqueta = document.body.querySelector<HTMLLabelElement>('label[for="filtro-test-1"]')
    expect(etiqueta?.textContent?.trim()).toBe('Sin etiquetas')
    document.body.querySelector<HTMLElement>('#filtro-test-1')?.click()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('update:modelValue')).toEqual([[['Mi etiqueta', '']]])
    wrapper.unmount()
  })

  describe('con un nombre masculino', () => {
    const propsMasculino = {
      ...propsBase,
      nombreSingular: 'tipo',
      nombrePlural: 'tipos',
      genero: 'masculino' as const,
    }

    it('con todos seleccionados muestra "Todos los tipos"', () => {
      const wrapper = mount(FiltroMultiple, { props: { ...propsMasculino, modelValue: [1, 2] } })

      expect(wrapper.get('button').text()).toBe('Todos los tipos')
    })

    it('sin selección muestra "Ningún tipo"', () => {
      const wrapper = mount(FiltroMultiple, { props: { ...propsMasculino, modelValue: [] } })

      expect(wrapper.get('button').text()).toBe('Ningún tipo')
    })
  })
})
