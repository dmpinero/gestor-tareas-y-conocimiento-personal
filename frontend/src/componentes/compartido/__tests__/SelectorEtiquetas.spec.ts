import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { DialogContent, DialogPortal, DialogRoot, DialogTitle } from 'reka-ui'
import SelectorEtiquetas from '../SelectorEtiquetas.vue'

const sugerenciasBase = ['Casa', 'Trabajo', 'Álgebra', 'Urgente']

function montar(
  props: Partial<{
    modelValue: string[]
    sugerencias: string[]
    longitudMaxima: number
    textoNuevo: string
  }> = {},
) {
  const valores = ref<string[]>(props.modelValue ?? [])
  const wrapper = mount(SelectorEtiquetas, {
    attachTo: document.body,
    props: {
      modelValue: valores.value,
      'onUpdate:modelValue': (nuevo: string[]) => {
        valores.value = nuevo
        void wrapper.setProps({ modelValue: nuevo })
      },
      sugerencias: props.sugerencias ?? sugerenciasBase,
      etiqueta: 'Etiquetas',
      id: 'campo-etiquetas',
      longitudMaxima: props.longitudMaxima ?? 50,
      textoNuevo: props.textoNuevo ?? 'Crear etiqueta "{valor}"',
    },
  })
  return { wrapper, valores }
}

async function escribir(wrapper: ReturnType<typeof montar>['wrapper'], texto: string) {
  await wrapper.get('input').setValue(texto)
  await flushPromises()
}

async function pulsar(wrapper: ReturnType<typeof montar>['wrapper'], tecla: string) {
  await wrapper.get('input').trigger('keydown', { key: tecla })
  await flushPromises()
}

function textosOpciones(wrapper: ReturnType<typeof montar>['wrapper']) {
  return wrapper.findAll('[role="option"]').map((opcion) => opcion.text())
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('SelectorEtiquetas', () => {
  it('muestra los valores seleccionados como chips con botón para quitarlos', () => {
    const { wrapper } = montar({ modelValue: ['Casa', 'Urgente'] })

    const chips = wrapper.findAll('[data-testid="chip"]')
    expect(chips.map((chip) => chip.text())).toEqual(['Casa', 'Urgente'])
    expect(wrapper.find('button[aria-label="Quitar Casa"]').exists()).toBe(true)
    expect(wrapper.find('button[aria-label="Quitar Urgente"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('quita un valor al pulsar su botón', async () => {
    const { wrapper, valores } = montar({ modelValue: ['Casa', 'Urgente'] })

    await wrapper.get('button[aria-label="Quitar Casa"]').trigger('click')
    await flushPromises()

    expect(valores.value).toEqual(['Urgente'])
    expect(wrapper.findAll('[data-testid="chip"]').map((chip) => chip.text())).toEqual(['Urgente'])
    wrapper.unmount()
  })

  it('el campo tiene etiqueta accesible y atributos de combobox', async () => {
    const { wrapper } = montar()

    const campo = wrapper.get('input')
    expect(campo.attributes('id')).toBe('campo-etiquetas')
    expect(campo.attributes('role')).toBe('combobox')
    expect(campo.attributes('aria-autocomplete')).toBe('list')
    expect(campo.attributes('aria-expanded')).toBe('false')
    const etiqueta = wrapper.get('label')
    expect(etiqueta.text()).toBe('Etiquetas')
    expect(etiqueta.attributes('for')).toBe('campo-etiquetas')

    await escribir(wrapper, 'a')

    expect(campo.attributes('aria-expanded')).toBe('true')
    const lista = wrapper.get('[role="listbox"]')
    expect(campo.attributes('aria-controls')).toBe(lista.attributes('id'))
    expect(lista.attributes('aria-label')).toBe('Etiquetas')
    wrapper.unmount()
  })

  it('filtra las sugerencias sin distinguir mayúsculas ni acentos', async () => {
    const { wrapper } = montar()

    await escribir(wrapper, 'ALGE')

    expect(textosOpciones(wrapper)).toEqual(['Álgebra', 'Crear etiqueta "ALGE"'])

    await escribir(wrapper, 'tra')

    expect(textosOpciones(wrapper)).toEqual(['Trabajo', 'Crear etiqueta "tra"'])
    wrapper.unmount()
  })

  it('excluye de las sugerencias los valores ya seleccionados', async () => {
    const { wrapper } = montar({ modelValue: ['casa'] })

    await escribir(wrapper, 'a')

    expect(textosOpciones(wrapper)).not.toContain('Casa')
    expect(textosOpciones(wrapper)).toContain('Trabajo')
    wrapper.unmount()
  })

  it('no ofrece crear si el texto coincide con una sugerencia o un valor seleccionado', async () => {
    const { wrapper } = montar({ modelValue: ['Urgente'] })

    await escribir(wrapper, 'casa')
    expect(textosOpciones(wrapper)).toEqual(['Casa'])

    await escribir(wrapper, 'URGENTE')
    expect(wrapper.find('[role="option"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('Enter con texto libre lo añade recortado y vacía el campo', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, '  Nueva etiqueta  ')
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual(['Nueva etiqueta'])
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('')
    expect(wrapper.get('input').attributes('aria-expanded')).toBe('false')
    wrapper.unmount()
  })

  it('al pulsar la opción de crear añade el texto escrito', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, 'Ocio')
    await wrapper.get('[role="option"]').trigger('mousedown')
    await wrapper.get('[role="option"]').trigger('click')
    await flushPromises()

    expect(valores.value).toEqual(['Ocio'])
    wrapper.unmount()
  })

  it('al pulsar una sugerencia la añade', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, 'trab')
    await wrapper.get('[role="option"]').trigger('click')
    await flushPromises()

    expect(valores.value).toEqual(['Trabajo'])
    wrapper.unmount()
  })

  it('si el texto coincide con una sugerencia usa la grafía de la sugerencia', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, 'TRABAJO')
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual(['Trabajo'])
    wrapper.unmount()
  })

  it('ignora el texto vacío o solo con espacios', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, '   \t ')
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual([])
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(wrapper.find('[role="option"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('rechaza valores más largos que la longitud máxima con un mensaje', async () => {
    const { wrapper, valores } = montar({ longitudMaxima: 5 })

    await escribir(wrapper, 'abcdef')
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual([])
    const error = wrapper.get('[role="alert"]')
    expect(error.text()).toBe('Máximo 5 caracteres.')
    const campo = wrapper.get('input')
    expect(campo.attributes('aria-invalid')).toBe('true')
    expect(campo.attributes('aria-describedby')).toBe(error.attributes('id'))

    await escribir(wrapper, 'abcde')

    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
    expect(campo.attributes('aria-invalid')).toBeUndefined()
    await pulsar(wrapper, 'Enter')
    expect(valores.value).toEqual(['abcde'])
    wrapper.unmount()
  })

  it('ignora duplicados sin distinguir mayúsculas', async () => {
    const { wrapper, valores } = montar({ modelValue: ['Ocio'] })

    await escribir(wrapper, 'OCIO')
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual(['Ocio'])
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('')
    wrapper.unmount()
  })

  it('Retroceso con el campo vacío quita el último valor', async () => {
    const { wrapper, valores } = montar({ modelValue: ['Casa', 'Urgente'] })

    await pulsar(wrapper, 'Backspace')

    expect(valores.value).toEqual(['Casa'])
    wrapper.unmount()
  })

  it('Retroceso con texto escrito no quita valores', async () => {
    const { wrapper, valores } = montar({ modelValue: ['Casa'] })

    await escribir(wrapper, 'x')
    await pulsar(wrapper, 'Backspace')

    expect(valores.value).toEqual(['Casa'])
    wrapper.unmount()
  })

  it('las flechas mueven la opción activa y Enter elige la activa', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, 'a')
    const campo = wrapper.get('input')
    expect(campo.attributes('aria-activedescendant')).toBeUndefined()

    await pulsar(wrapper, 'ArrowDown')
    let opciones = wrapper.findAll('[role="option"]')
    expect(campo.attributes('aria-activedescendant')).toBe(opciones[0]!.attributes('id'))
    expect(opciones[0]!.attributes('aria-selected')).toBe('true')

    await pulsar(wrapper, 'ArrowDown')
    opciones = wrapper.findAll('[role="option"]')
    expect(campo.attributes('aria-activedescendant')).toBe(opciones[1]!.attributes('id'))
    expect(opciones[0]!.attributes('aria-selected')).toBe('false')

    await pulsar(wrapper, 'ArrowUp')
    await pulsar(wrapper, 'ArrowUp')
    opciones = wrapper.findAll('[role="option"]')
    expect(campo.attributes('aria-activedescendant')).toBe(
      opciones[opciones.length - 1]!.attributes('id'),
    )

    await pulsar(wrapper, 'ArrowDown')
    await pulsar(wrapper, 'ArrowDown')
    const elegida = wrapper.findAll('[role="option"]')[1]!.text()
    await pulsar(wrapper, 'Enter')

    expect(valores.value).toEqual([elegida])
    wrapper.unmount()
  })

  it('Escape cierra la lista sin borrar el texto', async () => {
    const { wrapper, valores } = montar()

    await escribir(wrapper, 'tra')
    await pulsar(wrapper, 'Escape')

    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
    expect(wrapper.get('input').attributes('aria-expanded')).toBe('false')
    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('tra')
    expect(valores.value).toEqual([])

    await pulsar(wrapper, 'ArrowDown')
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)
    wrapper.unmount()
  })

  it('funciona dentro de un diálogo de reka-ui', async () => {
    const valores = ref<string[]>([])
    const contenedor = defineComponent({
      setup() {
        return () =>
          h(DialogRoot, { open: true }, () =>
            h(DialogPortal, null, () =>
              h(DialogContent, { 'aria-describedby': undefined }, () => [
                h(DialogTitle, null, () => 'Tarea'),
                h(SelectorEtiquetas, {
                  modelValue: valores.value,
                  'onUpdate:modelValue': (nuevo: string[]) => (valores.value = nuevo),
                  sugerencias: sugerenciasBase,
                  etiqueta: 'Asignado a',
                  longitudMaxima: 100,
                }),
              ]),
            ),
          )
      },
    })
    const wrapper = mount(contenedor, { attachTo: document.body })
    await flushPromises()

    const campo = document.body.querySelector<HTMLInputElement>('input[role="combobox"]')!
    expect(campo).not.toBeNull()
    campo.value = 'urg'
    campo.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(document.body.querySelectorAll('[role="option"]')).toHaveLength(2)

    // Escape con la lista abierta solo cierra la lista, no el diálogo.
    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()
    expect(document.body.querySelector('[role="listbox"]')).toBeNull()
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()

    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    await flushPromises()
    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }))
    await flushPromises()
    campo.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }))
    await flushPromises()

    expect(valores.value).toEqual(['Urgente'])
    expect(document.body.querySelector('button[aria-label="Quitar Urgente"]')).not.toBeNull()
    wrapper.unmount()
  })
})
