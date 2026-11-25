import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { GrupoEstados, Tarea } from '@/api/tipos'
import { useTiendaTareas } from '@/stores/tareas'
import TableroTareas from '../TableroTareas.vue'

vi.mock('@/api/cliente', () => ({
  clienteApi: {
    obtener: vi.fn<(...args: unknown[]) => unknown>(),
    crear: vi.fn<(...args: unknown[]) => unknown>(),
    actualizar: vi.fn<(...args: unknown[]) => unknown>(),
    parchear: vi.fn<(...args: unknown[]) => unknown>(),
    eliminar: vi.fn<(...args: unknown[]) => unknown>(),
  },
}))

const CLAVE_AGRUPAR = 'gestor-tareas:agrupar-subestado-tablero'
const CLAVE_PLEGADOS = 'gestor-tareas:subestados-plegados-tablero'
const CLAVE_MODO_ORDEN = 'gestor-tareas:modo-orden-tablero'
const CLAVE_ORDEN = 'gestor-tareas:orden-tablero'

const GRUPO: GrupoEstados = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 5,
  estados: [
    { id: 10, nombre: 'Pendiente', posicion: 1, tareas: 4 },
    { id: 11, nombre: 'En curso', posicion: 2, tareas: 0 },
    { id: 12, nombre: 'Hecho', posicion: 3, tareas: 1 },
  ],
}

const PENDIENTE = { id: 10, nombre: 'Pendiente' }
const HECHO = { id: 12, nombre: 'Hecho' }

function tarea(
  id: number,
  nombre: string,
  estado: { id: number; nombre: string },
  subestado: string | null,
): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: { id: 1, nombre: 'Desarrollo' },
    estado,
    workflow: null,
    subestado,
    congelada_en: null,
    hibernada_desde: null,
  }
}

const INFORME = tarea(1, 'Informe', PENDIENTE, 'En espera')
const ARTICULO = tarea(2, 'Artículo', PENDIENTE, 'Bloqueado')
const LLAMADA = tarea(3, 'Llamada', PENDIENTE, null)
const REVISION = tarea(4, 'Revisión', PENDIENTE, 'Bloqueado')
const DESPLIEGUE = tarea(5, 'Despliegue', HECHO, 'Bloqueado')
const TAREAS = [INFORME, ARTICULO, LLAMADA, REVISION, DESPLIEGUE]

let envoltorio: VueWrapper | null = null

async function montar(tareas: Tarea[] = TAREAS): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  const tienda = useTiendaTareas()
  tienda.tareas = structuredClone(tareas)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:ruta(.*)*', component: { render: () => null } }],
  })
  const contenedor = defineComponent({
    setup() {
      const idGrupo = ref<number | null>(1)
      return () =>
        h(TableroTareas, {
          tareas: tienda.tareas,
          grupos: [GRUPO],
          idGrupo: idGrupo.value,
          'onUpdate:idGrupo': (id: number | null) => {
            idGrupo.value = id
          },
        })
    },
  })
  envoltorio = mount(contenedor, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return envoltorio
}

function botonAgrupar(): HTMLButtonElement {
  const boton = [...document.body.querySelectorAll<HTMLButtonElement>('button')].find(
    (b) => b.textContent?.trim() === 'Agrupar por subestado',
  )
  if (!boton) throw new Error('No se encontró el botón "Agrupar por subestado"')
  return boton
}

const CLAVE_TARJETAS_POR_FILA = 'gestor-tareas:tarjetas-por-fila-tablero'

function opcion(etiqueta: '1' | '2'): HTMLInputElement {
  const grupo = document.body.querySelector<HTMLElement>(
    '[role="radiogroup"][aria-labelledby="tablero-tarjetas-por-fila"]',
  )
  if (!grupo) throw new Error('No se encontró el grupo "Tarjetas por fila"')
  const radio = [...grupo.querySelectorAll<HTMLInputElement>('input[type="radio"]')].find(
    (entrada) =>
      document.querySelector(`label[for="${entrada.id}"]`)?.textContent?.trim() === etiqueta,
  )
  if (!radio) throw new Error(`No se encontró la opción "${etiqueta}"`)
  return radio
}

function listasDe(nombre: string): HTMLElement[] {
  return [
    ...document.body.querySelectorAll<HTMLElement>(
      `section[aria-label="Estado ${nombre}"] ul[aria-label^="Tareas en ${nombre}"]`,
    ),
  ]
}

async function elegir(etiqueta: '1' | '2'): Promise<void> {
  const radio = opcion(etiqueta)
  radio.checked = true
  radio.dispatchEvent(new Event('change'))
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  for (const clave of [
    CLAVE_TARJETAS_POR_FILA,
    CLAVE_AGRUPAR,
    CLAVE_PLEGADOS,
    CLAVE_MODO_ORDEN,
    CLAVE_ORDEN,
  ]) {
    localStorage.removeItem(clave)
  }
})

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
  localStorage.removeItem(CLAVE_TARJETAS_POR_FILA)
})

describe('TableroTareas: tarjetas por fila', () => {
  it('junto a "Agrupar por subestado" ofrece 1 o 2 tarjetas por fila, con 1 por defecto', async () => {
    await montar()

    expect(document.getElementById('tablero-tarjetas-por-fila')?.textContent?.trim()).toBe(
      'Tarjetas por fila',
    )
    expect(opcion('1').checked).toBe(true)
    expect(opcion('2').checked).toBe(false)
    for (const lista of listasDe('Pendiente')) {
      expect(lista.classList.contains('grid-cols-2')).toBe(false)
    }
    // El selector va justo después del botón de agrupar.
    const agrupar = botonAgrupar()
    const grupo = document.querySelector('[aria-labelledby="tablero-tarjetas-por-fila"]')!
    expect(agrupar.compareDocumentPosition(grupo) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('con 2 tarjetas por fila, cada estado las coloca en dos columnas', async () => {
    await montar()

    await elegir('2')

    expect(opcion('2').checked).toBe(true)
    for (const nombre of ['Pendiente', 'Hecho']) {
      for (const lista of listasDe(nombre)) {
        expect(lista.classList.contains('grid-cols-2')).toBe(true)
      }
    }
    await elegir('1')
    for (const lista of listasDe('Pendiente')) {
      expect(lista.classList.contains('grid-cols-2')).toBe(false)
    }
  })

  it('también se aplica a cada bloque cuando se agrupa por subestado', async () => {
    await montar()
    await elegir('2')

    botonAgrupar().click()
    await flushPromises()

    const listas = listasDe('Pendiente')
    expect(listas.length).toBeGreaterThan(1)
    for (const lista of listas) expect(lista.classList.contains('grid-cols-2')).toBe(true)
  })

  it('recuerda la elección e ignora un valor guardado no válido', async () => {
    await montar()
    await elegir('2')
    expect(localStorage.getItem(CLAVE_TARJETAS_POR_FILA)).toBe('2')
    envoltorio?.unmount()
    document.body.innerHTML = ''

    await montar()
    expect(opcion('2').checked).toBe(true)
    envoltorio?.unmount()
    document.body.innerHTML = ''

    localStorage.setItem(CLAVE_TARJETAS_POR_FILA, '7')
    await montar()
    expect(opcion('1').checked).toBe(true)
  })
})
