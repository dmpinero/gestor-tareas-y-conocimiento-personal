import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { Foco, GrupoEstados, Subtarea, Tarea } from '@/api/tipos'
import { useTiendaFoco } from '@/stores/foco'
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

const GRUPO: GrupoEstados = {
  id: 1,
  nombre: 'Desarrollo',
  tareas: 3,
  estados: [{ id: 10, nombre: 'Pendiente', posicion: 1, tareas: 3 }],
}

function subtarea(id: number, nombre: string, asignado: string | null): Subtarea {
  return { id, nombre, asignado, prioridad: null, resuelta: false, comentarios: 0 }
}

function tarea(id: number, nombre: string, asignados: string[], subtareas: Subtarea[]): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:00:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados,
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas,
    grupo_estados: { id: 1, nombre: 'Desarrollo' },
    estado: { id: 10, nombre: 'Pendiente' },
    workflow: null,
    vinculadas: [],
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
  }
}

const PROPIA = tarea(1, 'Propia de José', ['José Manuel Viega'], [subtarea(10, 'Otra cosa', 'Ana')])
const CON_SUBTAREA = tarea(
  2,
  'Con subtarea de José',
  ['Ana'],
  [subtarea(20, 'Revisar oferta', 'José Manuel Viega'), subtarea(21, 'Llamar', 'Ana')],
)
const AJENA = tarea(3, 'Ajena', ['Ana'], [subtarea(30, 'Preparar', null)])
const TAREAS = [PROPIA, CON_SUBTAREA, AJENA]

let envoltorio: VueWrapper | null = null
const personas = ref<string[]>([])

async function montar(
  personasResaltadas: string[],
  foco: Foco | null = null,
  tareas: Tarea[] = TAREAS,
): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  useTiendaFoco().foco = foco
  const tienda = useTiendaTareas()
  tienda.tareas = JSON.parse(JSON.stringify(tareas)) as Tarea[]
  personas.value = personasResaltadas
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
          personasResaltadas: personas.value,
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

// Texto visible: sin lo que solo leen los lectores de pantalla.
function textoVisible(elemento: Element): string {
  const copia = elemento.cloneNode(true) as Element
  copia.querySelectorAll('.sr-only').forEach((oculto) => oculto.remove())
  return copia.textContent!.trim()
}

function tarjetasResaltadas(): string[] {
  return [...document.body.querySelectorAll('[data-tarjeta][data-resaltada]')].map((t) =>
    textoVisible(t.querySelector('[data-nombre-tarjeta]')!),
  )
}

function subtareasVisibles(): string[] {
  return [...document.body.querySelectorAll('[data-nombre-subtarea]')].map(textoVisible)
}

function subtareasResaltadas(): string[] {
  return [...document.body.querySelectorAll('[data-subtarea][data-resaltada]')].map((s) =>
    textoVisible(s.querySelector('[data-nombre-subtarea]')!),
  )
}

afterEach(() => {
  localStorage.clear()
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

function foco(tareaId: number, subtareaId: number | null = null): Foco {
  return {
    tarea_id: tareaId,
    tarea_nombre: 'x',
    subtarea_id: subtareaId,
    subtarea_nombre: subtareaId === null ? null : 'y',
    desde: '2026-11-24T10:00:00',
  }
}

function nombresTarjetas(): string[] {
  return [...document.body.querySelectorAll('[data-tarjeta]')].map((t) =>
    textoVisible(t.querySelector('[data-nombre-tarjeta]')!),
  )
}

function tarjetaDe(nombre: string): Element {
  return [...document.body.querySelectorAll('[data-tarjeta]')].find(
    (t) => textoVisible(t.querySelector('[data-nombre-tarjeta]')!) === nombre,
  )!
}

describe('TableroTareas: tarea en foco', () => {
  it('sin foco ninguna tarjeta ni subtarea está en foco', async () => {
    await montar([])

    expect(
      document.body.querySelectorAll('[data-en-foco="true"]:not([data-boton-foco])'),
    ).toHaveLength(0)
    expect(nombresTarjetas()).toEqual(['Propia de José', 'Con subtarea de José', 'Ajena'])
  })

  it('marca la tarjeta en foco con borde violeta e insignia "En foco" y la sube a lo alto de su columna', async () => {
    await montar([], foco(3))

    const tarjeta = tarjetaDe('Ajena')
    expect(tarjeta.getAttribute('data-en-foco')).toBe('true')
    expect(tarjeta.className).toContain('ring-violet-500')
    expect(tarjeta.querySelector('[data-insignia-foco]')?.textContent?.trim()).toBe('En foco')
    expect(nombresTarjetas()).toEqual(['Ajena', 'Propia de José', 'Con subtarea de José'])
    expect(tarjetaDe('Propia de José').getAttribute('data-en-foco')).toBeNull()
  })

  it('con una subtarea en foco despliega su tarjeta, sube la tarjeta y marca solo la subtarea', async () => {
    await montar([], foco(3, 30))

    expect(nombresTarjetas()[0]).toBe('Ajena')
    expect(tarjetaDe('Ajena').getAttribute('data-en-foco')).toBeNull()
    const enFoco = [...document.body.querySelectorAll('[data-subtarea][data-en-foco="true"]')]
    expect(enFoco.map((s) => textoVisible(s.querySelector('[data-nombre-subtarea]')!))).toEqual([
      'Preparar',
    ])
    expect(enFoco[0]!.querySelector('[data-insignia-foco]')).not.toBeNull()
    expect(enFoco[0]!.className).toContain('ring-violet-500')
  })

  it('al quitar el foco de la subtarea pliega la tarjeta que se desplegó por él', async () => {
    await montar([], foco(3, 30))

    useTiendaFoco().foco = null
    await flushPromises()

    expect(subtareasVisibles()).toEqual([])
  })

  it('el despliegue por foco no interfiere con el del filtro de personas', async () => {
    await montar(['José Manuel Viega'], foco(3, 30))

    // La tarjeta con la subtarea en foco va primero en la columna.
    expect(subtareasVisibles()).toEqual(['Preparar', 'Revisar oferta', 'Llamar'])
    expect(subtareasResaltadas()).toEqual(['Revisar oferta'])

    personas.value = []
    await flushPromises()

    expect(subtareasVisibles()).toEqual(['Preparar'])
  })

  it('"Trabajar en esta" de una tarjeta la pone en foco con PUT /foco', async () => {
    const { clienteApi } = await import('@/api/cliente')
    vi.mocked(clienteApi.actualizar).mockResolvedValue(foco(2))
    await montar([])

    tarjetaDe('Con subtarea de José')
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Trabajar en esta (Con subtarea de José)"]',
      )!
      .click()
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 2, subtarea_id: null })
    expect(tarjetaDe('Con subtarea de José').getAttribute('data-en-foco')).toBe('true')
    expect(
      tarjetaDe('Con subtarea de José').querySelector(
        'button[aria-label="Dejar de trabajar (Con subtarea de José)"]',
      ),
    ).not.toBeNull()
  })

  it('cada subtarea del tablero tiene su "Trabajar en esta"', async () => {
    const { clienteApi } = await import('@/api/cliente')
    vi.mocked(clienteApi.actualizar).mockResolvedValue(foco(1, 10))
    await montar([])
    document.body
      .querySelector<HTMLButtonElement>('button[aria-label="1 subtareas de Propia de José"]')!
      .click()
    await flushPromises()

    const fila = document.body.querySelector('[data-subtarea]')!
    fila
      .querySelector<HTMLButtonElement>('button[aria-label="Trabajar en esta (Otra cosa)"]')!
      .click()
    await flushPromises()

    expect(clienteApi.actualizar).toHaveBeenCalledWith('/foco', { tarea_id: 1, subtarea_id: 10 })
    expect(document.body.querySelector('[data-subtarea]')!.getAttribute('data-en-foco')).toBe(
      'true',
    )
  })

  it('"Añadir a siguientes" de una tarjeta la añade a la cola; no aparece en las completadas', async () => {
    const { clienteApi } = await import('@/api/cliente')
    vi.mocked(clienteApi.crear).mockResolvedValue([
      { tarea_id: 2, tarea_nombre: 'Con subtarea de José' },
    ])
    await montar([], null, [PROPIA, CON_SUBTAREA, { ...AJENA, completada: true }])

    tarjetaDe('Con subtarea de José')
      .querySelector<HTMLButtonElement>(
        'button[aria-label="Añadir a siguientes (Con subtarea de José)"]',
      )!
      .click()
    await flushPromises()

    expect(clienteApi.crear).toHaveBeenCalledWith('/siguientes', { tarea_id: 2 })
    expect(
      tarjetaDe('Con subtarea de José').querySelector(
        'button[aria-label="Quitar de siguientes (Con subtarea de José)"]',
      ),
    ).not.toBeNull()
    expect(tarjetaDe('Ajena').querySelector('[data-boton-siguientes]')).toBeNull()
  })

  describe('agrupado por subestado', () => {
    const CON_SUBESTADOS: Tarea[] = [
      { ...PROPIA, subestado: 'Bloqueado' },
      { ...CON_SUBTAREA, subestado: 'Bloqueado' },
      { ...AJENA, subestado: 'Esperando' },
    ]

    function bloques(): string[] {
      return [...document.body.querySelectorAll('[data-bloque-subestado]')].map(
        (b) => b.getAttribute('data-bloque-subestado') ?? '',
      )
    }

    it('el bloque con la tarjeta en foco va el primero de la columna', async () => {
      localStorage.setItem('gestor-tareas:agrupar-subestado-tablero', 'true')
      await montar([], foco(3), CON_SUBESTADOS)

      expect(nombresTarjetas()).toEqual(['Ajena', 'Propia de José', 'Con subtarea de José'])
      expect(bloques()[0]).toContain('Esperando')
    })

    it('con el foco en una subtarea, también sube el bloque de su tarjeta', async () => {
      localStorage.setItem('gestor-tareas:agrupar-subestado-tablero', 'true')
      await montar([], foco(2, 21), [
        { ...PROPIA, subestado: 'Esperando' },
        { ...CON_SUBTAREA, subestado: 'Zeta' },
        { ...AJENA, subestado: 'Bloqueado' },
      ])

      expect(nombresTarjetas()[0]).toBe('Con subtarea de José')
    })

    it('sin foco los bloques siguen en orden alfabético', async () => {
      localStorage.setItem('gestor-tareas:agrupar-subestado-tablero', 'true')
      await montar([], null, CON_SUBESTADOS)

      expect(nombresTarjetas()).toEqual(['Propia de José', 'Con subtarea de José', 'Ajena'])
    })
  })
})
