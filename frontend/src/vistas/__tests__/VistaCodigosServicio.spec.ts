import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { CodigoServicio } from '@/api/tipos'
import VistaCodigosServicio from '../VistaCodigosServicio.vue'

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const CODIGOS: CodigoServicio[] = [
  { id: 1, nombre: 'AXAS0024' },
  { id: 2, nombre: 'AXAS0026' },
]
const ID_NUEVO = '#nombre-codigo-servicio-nuevo'
const FORM_ALTA = 'form[aria-label="Añadir código de servicio"]'

let contenedor: VueWrapper | undefined

async function montar(codigos: CodigoServicio[] = CODIGOS): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(codigos))
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { template: '<div />' } },
      { path: '/ajustes/codigos-servicio', component: VistaCodigosServicio },
    ],
  })
  await enrutador.push('/ajustes/codigos-servicio')
  contenedor = mount(VistaCodigosServicio, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function nombres(vista: VueWrapper): string[] {
  return vista
    .findAll('[data-codigo-servicio] [data-testid="nombre-codigo-servicio"]')
    .map((n) => n.text())
}

function dialogo(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="alertdialog"]')
  if (!elemento) throw new Error('No se abrió la confirmación')
  return elemento
}

function botonDialogo(texto: string): HTMLButtonElement {
  const encontrado = [...dialogo().querySelectorAll('button')].find(
    (b) => b.textContent?.trim() === texto,
  )
  if (!encontrado) throw new Error(`No se encontró el botón "${texto}"`)
  return encontrado
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = undefined
  document.body.innerHTML = ''
})

describe('VistaCodigosServicio', () => {
  it('carga el catálogo y lo muestra', async () => {
    const vista = await montar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/codigos-servicio')
    expect(vista.get('h2').text()).toBe('Códigos de servicio')
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
    expect(vista.get('a[href="/ajustes"]').text()).toContain('Volver a Ajustes')
  })

  it('sin códigos lo indica', async () => {
    const vista = await montar([])

    expect(vista.text()).toContain('Todavía no hay códigos de servicio.')
  })

  it('añade un código recortado y lo coloca por orden alfabético', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.crear).mockResolvedValue({ id: 3, nombre: 'AXAS0025' })

    await vista.get(ID_NUEVO).setValue('  AXAS0025 ')
    await vista.get(FORM_ALTA).trigger('submit')
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/codigos-servicio', { nombre: 'AXAS0025' })
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0025', 'AXAS0026'])
    expect((vista.get(ID_NUEVO).element as HTMLInputElement).value).toBe('')
    expect(vista.find('[role="alert"]').exists()).toBe(false)
  })

  it.each([
    ['', 'El código de servicio debe tener al menos 2 caracteres.'],
    ['A', 'El código de servicio debe tener al menos 2 caracteres.'],
    ['A'.repeat(21), 'El código de servicio no puede superar los 20 caracteres.'],
    ['AX AS', 'El código de servicio no puede contener espacios.'],
  ])('no envía «%s» y explica por qué', async (nombre, mensaje) => {
    const vista = await montar()

    await vista.get(ID_NUEVO).setValue(nombre)
    await vista.get(FORM_ALTA).trigger('submit')
    await flushPromises()

    expect(vista.get('[role="alert"]').text()).toBe(mensaje)
    expect(vista.get(ID_NUEVO).attributes('aria-invalid')).toBe('true')
    expect(clienteApi.crear).not.toHaveBeenCalled()
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
  })

  it('muestra el error de la API si el código ya existe', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.crear).mockRejectedValue(
      new ErrorApi(409, 'Ya existe un código de servicio llamado «axas0024»'),
    )

    await vista.get(ID_NUEVO).setValue('axas0024')
    await vista.get(FORM_ALTA).trigger('submit')
    await flushPromises()

    expect(vista.get('[role="alert"]').text()).toBe(
      'Ya existe un código de servicio llamado «axas0024»',
    )
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
    expect((vista.get(ID_NUEVO).element as HTMLInputElement).value).toBe('axas0024')
  })

  it('renombra un código en línea', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ id: 1, nombre: 'AXAS0099' })

    await vista.get('button[aria-label="Renombrar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    const campo = vista.get('input[aria-label="Nuevo nombre del código de servicio AXAS0024"]')
    expect(document.activeElement).toBe(campo.element)
    await campo.setValue(' AXAS0099 ')
    await vista.get('form[aria-label="Renombrar código de servicio AXAS0024"]').trigger('submit')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/codigos-servicio/1', {
      nombre: 'AXAS0099',
    })
    expect(nombres(vista)).toEqual(['AXAS0026', 'AXAS0099'])
    expect(vista.find('form[aria-label^="Renombrar"]').exists()).toBe(false)
  })

  it('no renombra a un nombre inválido', async () => {
    const vista = await montar()

    await vista.get('button[aria-label="Renombrar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    await vista
      .get('input[aria-label="Nuevo nombre del código de servicio AXAS0024"]')
      .setValue('AX AS')
    await vista.get('form[aria-label="Renombrar código de servicio AXAS0024"]').trigger('submit')
    await flushPromises()

    expect(vista.get('[role="alert"]').text()).toBe(
      'El código de servicio no puede contener espacios.',
    )
    expect(clienteApi.actualizar).not.toHaveBeenCalled()
  })

  it('cancelar la edición deja el nombre como estaba', async () => {
    const vista = await montar()

    await vista.get('button[aria-label="Renombrar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    await vista
      .get('form[aria-label="Renombrar código de servicio AXAS0024"] button[type="button"]')
      .trigger('click')

    expect(clienteApi.actualizar).not.toHaveBeenCalled()
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
  })

  it('elimina un código tras confirmarlo', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    await vista.get('button[aria-label="Eliminar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    expect(dialogo().textContent).toContain('¿Eliminar el código de servicio AXAS0024?')
    botonDialogo('Eliminar').click()
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/codigos-servicio/1')
    expect(nombres(vista)).toEqual(['AXAS0026'])
    expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('si eliminar falla lo muestra en la confirmación y no lo quita', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.eliminar).mockRejectedValue(new ErrorApi(404, 'No existe'))

    await vista.get('button[aria-label="Eliminar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    botonDialogo('Eliminar').click()
    await flushPromises()

    expect(dialogo().textContent).toContain('No existe')
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
  })

  it('cancelar la confirmación no elimina nada', async () => {
    const vista = await montar()

    await vista.get('button[aria-label="Eliminar código de servicio AXAS0024"]').trigger('click')
    await flushPromises()
    botonDialogo('Cancelar').click()
    await flushPromises()

    expect(clienteApi.eliminar).not.toHaveBeenCalled()
    expect(nombres(vista)).toEqual(['AXAS0024', 'AXAS0026'])
  })
})
