import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi, ErrorApi } from '@/api/cliente'
import type { ElementoCatalogo } from '@/api/tipos'
import { colorEtiqueta } from '@/lib/coloresTarea'
import VistaSubestados from '../VistaSubestados.vue'

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

const SUBESTADOS: ElementoCatalogo[] = [
  { id: 1, nombre: 'Bloqueado' },
  { id: 2, nombre: 'En pausa' },
]

let contenedor: VueWrapper | undefined

async function montar(subestados: ElementoCatalogo[] = SUBESTADOS): Promise<VueWrapper> {
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(subestados))
  const enrutador = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: { template: '<div />' } },
      { path: '/ajustes/subestados', component: VistaSubestados },
    ],
  })
  await enrutador.push('/ajustes/subestados')
  contenedor = mount(VistaSubestados, {
    global: { plugins: [createPinia(), enrutador] },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function nombres(vista: VueWrapper): string[] {
  return vista.findAll('[data-subestado] [data-testid="pildora-subestado"]').map((p) => p.text())
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

describe('VistaSubestados', () => {
  it('carga el catálogo y muestra cada subestado como píldora de su color', async () => {
    const vista = await montar()

    expect(clienteApi.obtener).toHaveBeenCalledWith('/subestados')
    expect(vista.get('h2').text()).toBe('Subestados')
    expect(nombres(vista)).toEqual(['Bloqueado', 'En pausa'])
    const pildora = vista.get('[data-testid="pildora-subestado"]')
    for (const clase of colorEtiqueta('Bloqueado').split(' ')) {
      expect(pildora.classes()).toContain(clase)
    }
    expect(vista.get('a[href="/ajustes"]').text()).toContain('Volver a Ajustes')
  })

  it('sin subestados lo indica', async () => {
    const vista = await montar([])

    expect(vista.text()).toContain('Todavía no hay subestados.')
  })

  it('añade un subestado recortado y lo coloca por orden alfabético', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.crear).mockResolvedValue({ id: 3, nombre: 'Esperando cliente' })

    await vista.get('#nombre-subestado-nuevo').setValue('  Esperando cliente ')
    await vista.get('form[aria-label="Añadir subestado"]').trigger('submit')
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/subestados', { nombre: 'Esperando cliente' })
    expect(nombres(vista)).toEqual(['Bloqueado', 'En pausa', 'Esperando cliente'])
    expect((vista.get('#nombre-subestado-nuevo').element as HTMLInputElement).value).toBe('')
  })

  it('no envía un nombre vacío ni de más de 50 caracteres', async () => {
    const vista = await montar()

    await vista.get('form[aria-label="Añadir subestado"]').trigger('submit')
    await flushPromises()
    expect(vista.get('[role="alert"]').text()).toBe('El nombre del subestado es obligatorio.')

    await vista.get('#nombre-subestado-nuevo').setValue('a'.repeat(51))
    await vista.get('form[aria-label="Añadir subestado"]').trigger('submit')
    await flushPromises()
    expect(vista.get('[role="alert"]').text()).toBe(
      'El nombre del subestado no puede superar los 50 caracteres.',
    )
    expect(clienteApi.crear).not.toHaveBeenCalled()
  })

  it('muestra el error de la API si el nombre ya existe', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.crear).mockRejectedValue(
      new ErrorApi(409, 'Ya existe un subestado llamado «bloqueado»'),
    )

    await vista.get('#nombre-subestado-nuevo').setValue('bloqueado')
    await vista.get('form[aria-label="Añadir subestado"]').trigger('submit')
    await flushPromises()

    expect(vista.get('[role="alert"]').text()).toBe('Ya existe un subestado llamado «bloqueado»')
    expect(nombres(vista)).toEqual(['Bloqueado', 'En pausa'])
  })

  it('renombra un subestado en línea', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.actualizar).mockResolvedValue({ id: 1, nombre: 'Atascado' })

    await vista.get('button[aria-label="Renombrar subestado Bloqueado"]').trigger('click')
    await flushPromises()
    const campo = vista.get('input[aria-label="Nuevo nombre del subestado Bloqueado"]')
    expect(document.activeElement).toBe(campo.element)
    await campo.setValue(' Atascado ')
    await vista.get('form[aria-label="Renombrar subestado Bloqueado"]').trigger('submit')
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/subestados/1', { nombre: 'Atascado' })
    expect(nombres(vista)).toEqual(['Atascado', 'En pausa'])
  })

  it('elimina un subestado tras confirmarlo y avisa de que sus tareas quedan sin él', async () => {
    const vista = await montar()
    vi.mocked(clienteApi.eliminar).mockResolvedValue(undefined)

    await vista.get('button[aria-label="Eliminar subestado Bloqueado"]').trigger('click')
    await flushPromises()
    expect(dialogo().textContent).toContain('¿Eliminar el subestado Bloqueado?')
    expect(dialogo().textContent).toContain('Las tareas que lo tengan quedarán sin subestado.')
    botonDialogo('Eliminar').click()
    await flushPromises()

    expect(clienteApi.eliminar).toHaveBeenCalledWith('/subestados/1')
    expect(nombres(vista)).toEqual(['En pausa'])
    expect(document.body.querySelector('[role="alertdialog"]')).toBeNull()
  })

  it('cancelar la confirmación no elimina nada', async () => {
    const vista = await montar()

    await vista.get('button[aria-label="Eliminar subestado Bloqueado"]').trigger('click')
    await flushPromises()
    botonDialogo('Cancelar').click()
    await flushPromises()

    expect(clienteApi.eliminar).not.toHaveBeenCalled()
    expect(nombres(vista)).toEqual(['Bloqueado', 'En pausa'])
  })
})
