import { mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { Tarea } from '@/api/tipos'
import { RELLENO_PRIORIDAD, clavePrioridad } from '@/lib/coloresTarea'
import RedTareas from '../RedTareas.vue'

const CLAVE_UNIONES = 'gestor-tareas:uniones-red'

function tarea(id: number, nombre: string, cambios: Partial<Tarea> = {}): Tarea {
  return {
    id,
    nombre,
    prioridad: null,
    descripcion: '',
    fecha_creacion: '2026-11-10T09:30:00',
    fecha_vencimiento: null,
    etiquetas: [],
    asignados: [],
    tipo: null,
    oportunidad: null,
    completada: false,
    subtareas: [],
    grupo_estados: null,
    estado: null,
    workflow: null,
    subestado: null,
    congelada_en: null,
    hibernada_desde: null,
    vinculadas: [],
    ...cambios,
  }
}

// Informe y Factura comparten etiqueta y persona y están relacionadas; Demo
// comparte la etiqueta; Suelta no tiene nada en común.
const TAREAS = [
  tarea(1, 'Informe', {
    prioridad: 1,
    etiquetas: ['cliente-x'],
    asignados: ['Ana'],
    vinculadas: [2],
  }),
  tarea(2, 'Factura', {
    prioridad: 3,
    etiquetas: ['cliente-x'],
    asignados: ['Ana'],
    vinculadas: [1],
    completada: true,
  }),
  tarea(3, 'Demo', { etiquetas: ['cliente-x'] }),
  tarea(4, 'Suelta'),
]

let envoltorio: VueWrapper | null = null

function montar(tareas: Tarea[] = TAREAS) {
  envoltorio = mount(RedTareas, { props: { tareas }, attachTo: document.body })
  return envoltorio
}

function nodo(id: string) {
  const encontrado = envoltorio!.find(`[data-nodo="${id}"]`)
  if (!encontrado.exists()) throw new Error(`No se encontró el nodo ${id}`)
  return encontrado
}

function nodos(): string[] {
  return envoltorio!.findAll('[data-nodo]').map((n) => n.attributes('data-nodo')!)
}

function atenuados(): string[] {
  return envoltorio!
    .findAll('[data-nodo][data-atenuado="true"]')
    .map((n) => n.attributes('data-nodo')!)
}

function casilla(etiqueta: string) {
  const label = envoltorio!.findAll('label').find((l) => l.text() === etiqueta)
  if (!label) throw new Error(`No se encontró la casilla ${etiqueta}`)
  return label.find('input[type="checkbox"]')
}

function transformacion(): string {
  return envoltorio!.find('[data-testid="vista-red"]').attributes('transform')!
}

function boton(nombre: string) {
  const encontrado = envoltorio!.find(`button[aria-label="${nombre}"]`)
  if (!encontrado.exists()) throw new Error(`No se encontró el botón ${nombre}`)
  return encontrado
}

// jsdom no deja fijar `clientX` con `trigger`: se crea el evento a mano.
async function puntero(elemento: Element, tipo: string, x: number, y: number): Promise<void> {
  const constructorEvento = window.PointerEvent ?? window.MouseEvent
  elemento.dispatchEvent(
    new constructorEvento(tipo, { clientX: x, clientY: y, button: 0, bubbles: true }),
  )
  await envoltorio!.vm.$nextTick()
}

beforeEach(() => localStorage.removeItem(CLAVE_UNIONES))
afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  localStorage.removeItem(CLAVE_UNIONES)
})

describe('RedTareas', () => {
  it('dibuja las tareas, los nodos propios que unen 2 o más tareas y sus aristas', () => {
    montar()
    expect(nodos()).toEqual([
      'tarea:1',
      'tarea:2',
      'tarea:3',
      'tarea:4',
      'etiqueta:cliente-x',
      'persona:Ana',
    ])
    expect(envoltorio!.findAll('[data-arista]').map((a) => a.attributes('data-arista'))).toEqual([
      'tarea:1|tarea:2',
      'tarea:1|etiqueta:cliente-x',
      'tarea:2|etiqueta:cliente-x',
      'tarea:3|etiqueta:cliente-x',
      'tarea:1|persona:Ana',
      'tarea:2|persona:Ana',
    ])
    expect(nodo('tarea:1').text()).toContain('Informe')
    expect(nodo('etiqueta:cliente-x').text()).toContain('cliente-x')
  })

  it('colorea cada tarea con el color de su prioridad y atenúa las completadas', () => {
    montar([
      ...[1, 2, 3, 4, 5].map((p) => tarea(p, `P${p}`, { prioridad: p, etiquetas: ['E'] })),
      tarea(6, 'Sin', { completada: true, etiquetas: ['E'] }),
    ])
    for (const id of [1, 2, 3, 4, 5, 6]) {
      const clave = clavePrioridad(id === 6 ? null : id)
      const clases = nodo(`tarea:${id}`).find('[data-circulo]').classes()
      for (const clase of RELLENO_PRIORIDAD[clave].replace(/\bbg-/g, 'fill-').split(' ')) {
        expect(clases).toContain(clase)
      }
    }
    expect(nodo('tarea:6').attributes('data-completada')).toBe('true')
    expect(nodo('tarea:6').find('[data-circulo]').classes()).toContain('opacity-40')
    expect(nodo('tarea:1').attributes('data-completada')).toBe('false')
  })

  it('recorta los nombres largos y deja el nombre completo en el título', () => {
    const largo = 'Un nombre de tarea muy largo que no cabe'
    montar([tarea(1, largo, { vinculadas: [2] }), tarea(2, 'Otra', { vinculadas: [1] })])
    const texto = nodo('tarea:1').find('text').text()
    expect(texto.endsWith('…')).toBe(true)
    expect(texto.length).toBeLessThan(largo.length)
    expect(nodo('tarea:1').find('title').text()).toBe(largo)
  })

  it('da a cada nodo un nombre accesible y lo hace enfocable', () => {
    montar()
    expect(nodo('tarea:1').attributes('aria-label')).toBe('Tarea Informe: 3 conexiones')
    expect(nodo('tarea:3').attributes('aria-label')).toBe('Tarea Demo: 1 conexión')
    expect(nodo('tarea:2').attributes('aria-label')).toBe('Tarea Factura: 3 conexiones, completada')
    expect(nodo('tarea:4').attributes('aria-label')).toBe('Tarea Suelta: 0 conexiones')
    expect(nodo('etiqueta:cliente-x').attributes('aria-label')).toBe('Etiqueta cliente-x: 3 tareas')
    expect(nodo('persona:Ana').attributes('aria-label')).toBe('Persona Ana: 2 tareas')
    for (const id of nodos()) {
      expect(nodo(id).attributes('tabindex')).toBe('0')
      expect(nodo(id).attributes('role')).toBe('button')
    }
  })

  it('nombra los nodos de subestado y oportunidad', () => {
    const op = { codigo: 'OP7', descripcion: null, observaciones: null }
    montar([
      tarea(1, 'A', { subestado: 'Esperando', oportunidad: op }),
      tarea(2, 'B', { subestado: 'Esperando', oportunidad: op }),
    ])
    expect(nodo('subestado:Esperando').attributes('aria-label')).toBe(
      'Subestado Esperando: 2 tareas',
    )
    expect(nodo('oportunidad:OP7').attributes('aria-label')).toBe('Oportunidad OP7: 2 tareas')
  })

  it('muestra una leyenda', () => {
    montar()
    const leyenda = envoltorio!.find('[data-testid="leyenda-red"]').text()
    for (const texto of [
      'Prioridad 1',
      'Sin prioridad',
      'Completada',
      'Etiqueta',
      'Persona',
      'Subestado',
      'Oportunidad',
      'Tareas relacionadas',
    ]) {
      expect(leyenda).toContain(texto)
    }
  })

  describe('uniones', () => {
    it('todas las casillas están marcadas por defecto', () => {
      montar()
      for (const etiqueta of [
        'Relacionadas',
        'Etiquetas',
        'Personas',
        'Subestados',
        'Oportunidades',
      ]) {
        expect((casilla(etiqueta).element as HTMLInputElement).checked).toBe(true)
      }
    })

    it('al desmarcar una unión quita sus nodos y aristas y lo recuerda', async () => {
      montar()
      await casilla('Etiquetas').setValue(false)
      expect(nodos()).not.toContain('etiqueta:cliente-x')
      await casilla('Relacionadas').setValue(false)
      expect(envoltorio!.find('[data-arista="tarea:1|tarea:2"]').exists()).toBe(false)
      expect(JSON.parse(localStorage.getItem(CLAVE_UNIONES)!)).toEqual([
        'personas',
        'subestados',
        'oportunidades',
      ])

      envoltorio!.unmount()
      montar()
      expect((casilla('Etiquetas').element as HTMLInputElement).checked).toBe(false)
      expect((casilla('Personas').element as HTMLInputElement).checked).toBe(true)
      expect(nodos()).toContain('persona:Ana')
      expect(nodos()).not.toContain('etiqueta:cliente-x')
    })

    it('con una preferencia no válida marca todas', () => {
      localStorage.setItem(CLAVE_UNIONES, '{roto')
      montar()
      expect((casilla('Etiquetas').element as HTMLInputElement).checked).toBe(true)
    })
  })

  describe('resaltado', () => {
    it('al pasar el ratón por un nodo resalta sus vecinos y atenúa el resto', async () => {
      montar()
      expect(atenuados()).toEqual([])
      await nodo('persona:Ana').trigger('mouseenter')
      expect(atenuados()).toEqual(['tarea:3', 'tarea:4', 'etiqueta:cliente-x'])
      expect(envoltorio!.find('[data-arista="tarea:1|tarea:2"]').attributes('data-atenuado')).toBe(
        'true',
      )
      expect(
        envoltorio!.find('[data-arista="tarea:1|persona:Ana"]').attributes('data-atenuado'),
      ).toBe('false')
      await nodo('persona:Ana').trigger('mouseleave')
      expect(atenuados()).toEqual([])
    })

    it('al enfocar un nodo también resalta sus vecinos', async () => {
      montar()
      await nodo('tarea:3').trigger('focus')
      expect(atenuados()).toEqual(['tarea:1', 'tarea:2', 'tarea:4', 'persona:Ana'])
      await nodo('tarea:3').trigger('blur')
      expect(atenuados()).toEqual([])
    })

    it('un clic o Enter en un nodo propio fija el resaltado y otro lo quita', async () => {
      montar()
      const ana = nodo('persona:Ana')
      expect(ana.attributes('aria-pressed')).toBe('false')
      await ana.trigger('click')
      await ana.trigger('mouseleave')
      expect(ana.attributes('aria-pressed')).toBe('true')
      expect(atenuados()).toEqual(['tarea:3', 'tarea:4', 'etiqueta:cliente-x'])
      // Con el resaltado fijado, pasar por otro nodo no lo cambia.
      await nodo('tarea:4').trigger('mouseenter')
      expect(atenuados()).toEqual(['tarea:3', 'tarea:4', 'etiqueta:cliente-x'])
      await nodo('tarea:4').trigger('mouseleave')

      await ana.trigger('click')
      expect(ana.attributes('aria-pressed')).toBe('false')
      expect(atenuados()).toEqual([])

      await ana.trigger('keydown', { key: 'Enter' })
      expect(ana.attributes('aria-pressed')).toBe('true')
      await ana.trigger('keydown', { key: 'Enter' })
      expect(ana.attributes('aria-pressed')).toBe('false')
    })

    it('las tareas no tienen aria-pressed', () => {
      montar()
      expect(nodo('tarea:1').attributes('aria-pressed')).toBeUndefined()
    })
  })

  it('un clic, Enter o Espacio en una tarea pide ver su detalle', async () => {
    montar()
    await nodo('tarea:1').trigger('click')
    await nodo('tarea:3').trigger('keydown', { key: 'Enter' })
    await nodo('tarea:4').trigger('keydown', { key: ' ' })
    expect(envoltorio!.emitted('verDetalle')).toEqual([[1], [3], [4]])
  })

  describe('zoom y desplazamiento', () => {
    it('los botones acercan, alejan y ajustan la vista', async () => {
      montar()
      const inicial = transformacion()
      await boton('Acercar').trigger('click')
      const cerca = transformacion()
      expect(cerca).not.toBe(inicial)
      expect(cerca).toContain('scale(1.25)')
      await boton('Alejar').trigger('click')
      await boton('Alejar').trigger('click')
      expect(transformacion()).toContain('scale(0.8)')
      await boton('Ajustar').trigger('click')
      expect(transformacion()).toBe(inicial)
    })

    it('la rueda acerca y aleja', async () => {
      montar()
      const lienzo = envoltorio!.find('[data-testid="lienzo-red"]')
      await lienzo.trigger('wheel', { deltaY: -100 })
      expect(transformacion()).toContain('scale(1.25)')
      await lienzo.trigger('wheel', { deltaY: 100 })
      expect(transformacion()).toContain('scale(1)')
    })

    it('arrastrar el fondo desplaza la vista', async () => {
      montar()
      const inicial = transformacion()
      const fondo = envoltorio!.find('[data-testid="fondo-red"]')
      await puntero(fondo.element, 'pointerdown', 10, 10)
      await puntero(fondo.element, 'pointermove', 40, 30)
      await puntero(fondo.element, 'pointerup', 40, 30)
      const movida = transformacion()
      expect(movida).not.toBe(inicial)
      expect(movida.startsWith('translate(30 20)')).toBe(true)
      // Sin arrastrar, mover el puntero no cambia nada.
      await puntero(fondo.element, 'pointermove', 90, 90)
      expect(transformacion()).toBe(movida)
    })
  })

  describe('estados vacíos', () => {
    it('sin tareas', () => {
      montar([])
      expect(envoltorio!.text()).toContain('Ninguna tarea coincide con los filtros.')
      expect(envoltorio!.find('svg[data-testid="lienzo-red"]').exists()).toBe(false)
    })

    it('con tareas pero sin uniones visibles, deja cambiar las uniones', async () => {
      montar([tarea(1, 'A'), tarea(2, 'B')])
      expect(envoltorio!.text()).toContain(
        'Estas tareas no tienen nada en común con las uniones elegidas.',
      )
      expect(envoltorio!.find('svg[data-testid="lienzo-red"]').exists()).toBe(false)
      expect(casilla('Etiquetas').exists()).toBe(true)
    })

    it('al desmarcar todas las uniones aparece el aviso', async () => {
      montar()
      for (const etiqueta of ['Relacionadas', 'Etiquetas', 'Personas']) {
        await casilla(etiqueta).setValue(false)
      }
      expect(envoltorio!.text()).toContain(
        'Estas tareas no tienen nada en común con las uniones elegidas.',
      )
    })
  })
})
