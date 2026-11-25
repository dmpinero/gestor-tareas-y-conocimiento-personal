import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { clienteApi } from '@/api/cliente'
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

function columna(nombre: string): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>(
    `section[aria-label="Estado ${nombre}"]`,
  )
  if (!elemento) throw new Error(`No se encontró la columna "${nombre}"`)
  return elemento
}

function cabeceras(nombre: string): HTMLButtonElement[] {
  return [...columna(nombre).querySelectorAll<HTMLButtonElement>('button[data-cabecera-grupo]')]
}

// Nombre accesible de la cabecera: su texto sin lo que oculta a los lectores.
function nombreAccesible(boton: HTMLElement): string {
  const copia = boton.cloneNode(true) as HTMLElement
  copia.querySelectorAll('[aria-hidden="true"]').forEach((e) => e.remove())
  return copia.textContent!.replace(/\s+/g, ' ').trim()
}

function nombresGrupos(nombre: string): string[] {
  return cabeceras(nombre).map(nombreAccesible)
}

function cabecera(nombreColumna: string, grupo: string): HTMLButtonElement {
  const boton = cabeceras(nombreColumna).find((b) => nombreAccesible(b).startsWith(`${grupo} (`))
  if (!boton) throw new Error(`No se encontró el grupo "${grupo}" en "${nombreColumna}"`)
  return boton
}

function tarjetasDe(raiz: ParentNode): string[] {
  return [...raiz.querySelectorAll('[data-tarjeta] [data-nombre-tarjeta]')].map((t) =>
    t.textContent!.trim(),
  )
}

function bloque(nombreColumna: string, grupo: string): HTMLElement | null {
  const id = cabecera(nombreColumna, grupo).getAttribute('aria-controls')
  return id ? document.getElementById(id) : null
}

function contador(nombre: string): string {
  return columna(nombre).querySelector('[data-contador]')!.textContent!.trim()
}

function lanzarEventoArrastre(elemento: Element, tipo: string, dataTransfer: object): void {
  const evento = new Event(tipo, { bubbles: true, cancelable: true })
  Object.defineProperty(evento, 'dataTransfer', { value: dataTransfer })
  elemento.dispatchEvent(evento)
}

function crearDataTransfer(): object {
  return { effectAllowed: '', dropEffect: '', setData: vi.fn<() => void>() }
}

// Responde a los PATCH de estado y subestado con la tarea cambiada, como la API.
function simularRespuestas(): void {
  vi.mocked(clienteApi.parchear).mockImplementation(async (ruta: unknown, cuerpo: unknown) => {
    const id = Number(String(ruta).split('/')[2])
    const actual = useTiendaTareas().tareas.find((t) => t.id === id)!
    const datos = cuerpo as { estado_id?: number; subestado?: string | null }
    if (datos.estado_id !== undefined) {
      const estado = GRUPO.estados.find((e) => e.id === datos.estado_id)!
      return {
        ...JSON.parse(JSON.stringify(actual)),
        estado: { id: estado.id, nombre: estado.nombre },
      }
    }
    return { ...JSON.parse(JSON.stringify(actual)), subestado: datos.subestado ?? null }
  })
}

async function arrastrar(tarjeta: Element, destino: Element): Promise<void> {
  const dataTransfer = crearDataTransfer()
  lanzarEventoArrastre(tarjeta, 'dragstart', dataTransfer)
  lanzarEventoArrastre(destino, 'dragover', dataTransfer)
  await flushPromises()
  lanzarEventoArrastre(destino, 'drop', dataTransfer)
  lanzarEventoArrastre(tarjeta, 'dragend', dataTransfer)
  await flushPromises()
}

function anuncio(): string {
  return document.body.querySelector('[data-anuncio-tablero]')?.textContent?.trim() ?? ''
}

// Grupos marcados como destino, como "<columna>: <grupo>" (una vez por grupo).
function gruposMarcados(): string[] {
  const marcados = document.body.querySelectorAll<HTMLElement>('[data-destino-subestado]')
  return [
    ...new Set(
      [...marcados].map((m) => {
        const nombreColumna = m
          .closest('section')!
          .getAttribute('aria-label')!
          .replace('Estado ', '')
        return `${nombreColumna}: ${m.getAttribute('data-destino-subestado')}`
      }),
    ),
  ]
}

function limpiarAlmacen(): void {
  for (const clave of [CLAVE_AGRUPAR, CLAVE_PLEGADOS, CLAVE_MODO_ORDEN, CLAVE_ORDEN]) {
    localStorage.removeItem(clave)
  }
}

beforeEach(() => {
  limpiarAlmacen()
  vi.mocked(clienteApi.parchear).mockReset()
})

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  limpiarAlmacen()
  document.body.innerHTML = ''
})

describe('TableroTareas: agrupar por subestado', () => {
  it('el botón "Agrupar por subestado" empieza desactivado y el tablero no cambia', async () => {
    await montar()

    const boton = botonAgrupar()
    expect(boton.getAttribute('aria-pressed')).toBe('false')
    expect(document.body.querySelector('[data-cabecera-grupo]')).toBeNull()
    const lista = columna('Pendiente').querySelector('ul[aria-label="Tareas en Pendiente"]')!
    expect(tarjetasDe(lista)).toEqual(['Informe', 'Artículo', 'Llamada', 'Revisión'])
  })

  it('al activarlo agrupa las tarjetas de cada columna por subestado, con nombre y número, "Sin subestado" al final y sin grupos vacíos', async () => {
    await montar()

    botonAgrupar().click()
    await flushPromises()

    expect(botonAgrupar().getAttribute('aria-pressed')).toBe('true')
    expect(nombresGrupos('Pendiente')).toEqual([
      'Bloqueado (2 tareas)',
      'En espera (1 tarea)',
      'Sin subestado (1 tarea)',
    ])
    expect(tarjetasDe(bloque('Pendiente', 'Bloqueado')!)).toEqual(['Artículo', 'Revisión'])
    expect(tarjetasDe(bloque('Pendiente', 'En espera')!)).toEqual(['Informe'])
    expect(tarjetasDe(bloque('Pendiente', 'Sin subestado')!)).toEqual(['Llamada'])
    expect(nombresGrupos('Hecho')).toEqual(['Bloqueado (1 tarea)'])
    expect(cabeceras('En curso')).toEqual([])
    // El número de la columna sigue siendo el total.
    expect(contador('Pendiente')).toBe('4')
    // La píldora del subestado y su cabecera como encabezado de nivel 4.
    const pildora = cabecera('Pendiente', 'Bloqueado').querySelector('[data-pildora-grupo]')
    expect(pildora?.textContent?.trim()).toBe('Bloqueado')
    expect(cabecera('Pendiente', 'Bloqueado').closest('h4')).not.toBeNull()
    expect(localStorage.getItem(CLAVE_AGRUPAR)).toBe('true')
    // "Añadir tarea en {E}" no cambia.
    expect(
      columna('Pendiente').querySelector('button[aria-label="Añadir tarea en Pendiente"]'),
    ).not.toBeNull()

    botonAgrupar().click()
    await flushPromises()
    expect(document.body.querySelector('[data-cabecera-grupo]')).toBeNull()
    expect(localStorage.getItem(CLAVE_AGRUPAR)).toBe('false')
  })

  it('una línea horizontal separa cada grupo del anterior, sin línea antes del primero ni sin agrupar', async () => {
    await montar()
    expect(document.body.querySelector('[data-separador-subestado]')).toBeNull()

    botonAgrupar().click()
    await flushPromises()

    const separadores = [...columna('Pendiente').querySelectorAll('[data-separador-subestado]')]
    expect(separadores).toHaveLength(2)
    // Cada línea va justo antes de la cabecera del grupo que separa.
    expect(separadores.map((s) => nombreAccesible(s.nextElementSibling as HTMLElement))).toEqual([
      'En espera (1 tarea)',
      'Sin subestado (1 tarea)',
    ])
    for (const separador of separadores) {
      expect(separador.tagName).toBe('HR')
      expect(separador.getAttribute('aria-hidden')).toBe('true')
      // Del mismo color que el carril: Pendiente es el primero, gris.
      expect([...separador.classList]).toEqual(
        expect.arrayContaining(['border-gray-600', 'dark:border-gray-400']),
      )
    }
    // Una columna con un único grupo no lleva línea.
    expect(columna('Hecho').querySelector('[data-separador-subestado]')).toBeNull()
  })

  it('cada grupo se pliega y despliega con aria-expanded, solo en su columna, y se recuerda', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()

    const boton = cabecera('Pendiente', 'Bloqueado')
    expect(boton.getAttribute('aria-expanded')).toBe('true')
    const idBloque = boton.getAttribute('aria-controls')!
    expect(document.getElementById(idBloque)).not.toBeNull()

    boton.click()
    await flushPromises()

    expect(cabecera('Pendiente', 'Bloqueado').getAttribute('aria-expanded')).toBe('false')
    expect(cabecera('Pendiente', 'Bloqueado').hasAttribute('aria-controls')).toBe(false)
    expect(document.getElementById(idBloque)).toBeNull()
    expect(tarjetasDe(columna('Pendiente'))).toEqual(['Informe', 'Llamada'])
    // El mismo subestado en otra columna sigue desplegado.
    expect(cabecera('Hecho', 'Bloqueado').getAttribute('aria-expanded')).toBe('true')
    expect(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS)!)).toEqual(['10:subestado:Bloqueado'])

    cabecera('Pendiente', 'Bloqueado').click()
    await flushPromises()
    expect(cabecera('Pendiente', 'Bloqueado').getAttribute('aria-expanded')).toBe('true')
    expect(tarjetasDe(bloque('Pendiente', 'Bloqueado')!)).toEqual(['Artículo', 'Revisión'])
    expect(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS)!)).toEqual([])
  })

  it('recuerda la agrupación y los grupos plegados al volver', async () => {
    localStorage.setItem(CLAVE_AGRUPAR, 'true')
    localStorage.setItem(CLAVE_PLEGADOS, JSON.stringify(['10:sin', 7, '12:subestado:Bloqueado']))
    await montar()

    expect(botonAgrupar().getAttribute('aria-pressed')).toBe('true')
    expect(cabecera('Pendiente', 'Sin subestado').getAttribute('aria-expanded')).toBe('false')
    expect(cabecera('Pendiente', 'Bloqueado').getAttribute('aria-expanded')).toBe('true')
    expect(cabecera('Hecho', 'Bloqueado').getAttribute('aria-expanded')).toBe('false')
  })

  it.each([
    ['sí', 'no es JSON'],
    ['1', '{"10:subestado:Bloqueado":true}'],
    ['{}', '"10:subestado:Bloqueado"'],
  ])('ignora valores guardados no válidos (agrupar %s, plegados %s)', async (agrupar, plegados) => {
    localStorage.setItem(CLAVE_AGRUPAR, agrupar)
    localStorage.setItem(CLAVE_PLEGADOS, plegados)
    await montar()

    expect(botonAgrupar().getAttribute('aria-pressed')).toBe('false')
    botonAgrupar().click()
    await flushPromises()
    expect(cabeceras('Pendiente').map((b) => b.getAttribute('aria-expanded'))).toEqual([
      'true',
      'true',
      'true',
    ])
  })

  it('"Mover a…" solo cambia el estado; el foco queda en su "Mover a…" y se despliega su grupo si estaba plegado', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    cabecera('Hecho', 'Bloqueado').click()
    await flushPromises()
    vi.mocked(clienteApi.parchear).mockResolvedValue({
      ...structuredClone(ARTICULO),
      estado: HECHO,
    })

    columna('Pendiente')
      .querySelector<HTMLButtonElement>('button[aria-label="Mover a… (Artículo)"]')!
      .click()
    await flushPromises()
    const menu = document.body.querySelector<HTMLElement>('[data-menu-mover]')!
    ;[...menu.querySelectorAll('button')].find((b) => b.textContent?.trim() === 'Hecho')!.click()
    await flushPromises()

    expect(clienteApi.parchear).toHaveBeenCalledWith('/tareas/2/estado', { estado_id: 12 })
    expect(cabecera('Hecho', 'Bloqueado').getAttribute('aria-expanded')).toBe('true')
    expect(tarjetasDe(bloque('Hecho', 'Bloqueado')!)).toEqual(['Artículo', 'Despliegue'])
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Mover a… (Artículo)')
    expect(bloque('Hecho', 'Bloqueado')!.contains(document.activeElement)).toBe(true)
    expect(JSON.parse(localStorage.getItem(CLAVE_PLEGADOS)!)).toEqual([])
    expect(contador('Hecho')).toBe('2')
  })

  it('soltar una tarjeta sobre un grupo de otra columna cambia su estado y su subestado', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    simularRespuestas()
    const tarjeta = bloque('Pendiente', 'En espera')!.querySelector('[data-tarjeta]')!
    const destino = cabecera('Hecho', 'Bloqueado')

    await arrastrar(tarjeta, destino)

    expect(vi.mocked(clienteApi.parchear).mock.calls).toEqual([
      ['/tareas/1/estado', { estado_id: 12 }],
      ['/tareas/1/subestado', { subestado: 'Bloqueado' }],
    ])
    expect(nombresGrupos('Hecho')).toEqual(['Bloqueado (2 tareas)'])
    expect(tarjetasDe(bloque('Hecho', 'Bloqueado')!)).toEqual(['Informe', 'Despliegue'])
    expect(nombresGrupos('Pendiente')).toEqual(['Bloqueado (2 tareas)', 'Sin subestado (1 tarea)'])
    expect(anuncio()).toBe('Informe movida a Hecho, Bloqueado')
  })

  it('soltar una tarjeta sobre otro grupo de su columna solo cambia su subestado', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    simularRespuestas()
    const tarjeta = bloque('Pendiente', 'En espera')!.querySelector('[data-tarjeta]')!
    // Sobre una tarjeta del grupo de destino, no solo sobre su cabecera.
    const destino = bloque('Pendiente', 'Bloqueado')!.querySelector('[data-tarjeta]')!

    await arrastrar(tarjeta, destino)

    expect(vi.mocked(clienteApi.parchear).mock.calls).toEqual([
      ['/tareas/1/subestado', { subestado: 'Bloqueado' }],
    ])
    expect(nombresGrupos('Pendiente')).toEqual(['Bloqueado (3 tareas)', 'Sin subestado (1 tarea)'])
    expect(anuncio()).toBe('Informe movida a Bloqueado')
  })

  it('soltarla en "Sin subestado" le quita el subestado', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    simularRespuestas()
    const tarjeta = bloque('Pendiente', 'Bloqueado')!.querySelector('[data-tarjeta]')!

    await arrastrar(tarjeta, cabecera('Pendiente', 'Sin subestado'))

    expect(vi.mocked(clienteApi.parchear).mock.calls).toEqual([
      ['/tareas/2/subestado', { subestado: null }],
    ])
    expect(tarjetasDe(bloque('Pendiente', 'Sin subestado')!)).toEqual(['Artículo', 'Llamada'])
    expect(anuncio()).toBe('Artículo movida a Sin subestado')
  })

  it('soltarla en su mismo grupo, o en su columna fuera de los grupos, no cambia nada', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    simularRespuestas()
    const tarjeta = bloque('Pendiente', 'Bloqueado')!.querySelector('[data-tarjeta]')!

    await arrastrar(tarjeta, cabecera('Pendiente', 'Bloqueado'))
    await arrastrar(tarjeta, columna('Pendiente').querySelector('h3')!)

    expect(clienteApi.parchear).not.toHaveBeenCalled()
    expect(nombresGrupos('Pendiente')).toEqual([
      'Bloqueado (2 tareas)',
      'En espera (1 tarea)',
      'Sin subestado (1 tarea)',
    ])
  })

  it('soltarla en otra columna fuera de sus grupos solo cambia su estado', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    simularRespuestas()
    const tarjeta = bloque('Pendiente', 'En espera')!.querySelector('[data-tarjeta]')!

    await arrastrar(tarjeta, columna('Hecho').querySelector('h3')!)

    expect(vi.mocked(clienteApi.parchear).mock.calls).toEqual([
      ['/tareas/1/estado', { estado_id: 12 }],
    ])
    expect(nombresGrupos('Hecho')).toEqual(['Bloqueado (1 tarea)', 'En espera (1 tarea)'])
  })

  it('marca el grupo sobre el que se arrastra, y solo ese', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    const tarjeta = bloque('Pendiente', 'En espera')!.querySelector('[data-tarjeta]')!
    const dataTransfer = crearDataTransfer()

    lanzarEventoArrastre(tarjeta, 'dragstart', dataTransfer)
    lanzarEventoArrastre(cabecera('Hecho', 'Bloqueado'), 'dragover', dataTransfer)
    await flushPromises()
    expect(gruposMarcados()).toEqual(['Hecho: Bloqueado'])

    lanzarEventoArrastre(columna('Hecho').querySelector('h3')!, 'dragover', dataTransfer)
    await flushPromises()
    expect(gruposMarcados()).toEqual([])

    lanzarEventoArrastre(tarjeta, 'dragend', dataTransfer)
    await flushPromises()
    expect(gruposMarcados()).toEqual([])
  })

  it('si falla el cambio de subestado, la tarjeta sigue en su grupo y se muestra el error', async () => {
    await montar()
    botonAgrupar().click()
    await flushPromises()
    vi.mocked(clienteApi.parchear).mockRejectedValue(new Error('Fallo de red'))
    const tarjeta = bloque('Pendiente', 'En espera')!.querySelector('[data-tarjeta]')!

    await arrastrar(tarjeta, cabecera('Pendiente', 'Bloqueado'))

    expect(useTiendaTareas().error).toBe('Fallo de red')
    expect(tarjetasDe(bloque('Pendiente', 'En espera')!)).toEqual(['Informe'])
    expect(anuncio()).toBe('')
  })

  it('en orden manual, "Subir" y "Bajar" mueven la tarjeta dentro de su grupo', async () => {
    localStorage.setItem(CLAVE_MODO_ORDEN, 'manual')
    await montar()
    botonAgrupar().click()
    await flushPromises()

    const mover = columna('Pendiente').querySelector<HTMLButtonElement>(
      'button[aria-label="Mover a… (Artículo)"]',
    )!
    mover.click()
    await flushPromises()
    let menu = document.body.querySelector<HTMLElement>('[data-menu-mover]')!
    // Es la primera de su grupo: no se puede subir, aunque no sea la primera de la columna.
    expect(menu.querySelector('button[aria-label="Subir Artículo una posición"]')).toBeNull()
    menu
      .querySelector<HTMLButtonElement>('button[aria-label="Bajar Artículo una posición"]')!
      .click()
    await flushPromises()

    expect(tarjetasDe(bloque('Pendiente', 'Bloqueado')!)).toEqual(['Revisión', 'Artículo'])
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Mover a… (Artículo)')
    expect(document.body.querySelector('[data-anuncio-tablero]')?.textContent).toBe(
      'Artículo en la posición 2 de Bloqueado en Pendiente',
    )

    columna('Pendiente')
      .querySelector<HTMLButtonElement>('button[aria-label="Mover a… (Artículo)"]')!
      .click()
    await flushPromises()
    menu = document.body.querySelector<HTMLElement>('[data-menu-mover]')!
    expect(menu.querySelector('button[aria-label="Bajar Artículo una posición"]')).toBeNull()
    menu
      .querySelector<HTMLButtonElement>('button[aria-label="Subir Artículo una posición"]')!
      .click()
    await flushPromises()
    expect(tarjetasDe(bloque('Pendiente', 'Bloqueado')!)).toEqual(['Artículo', 'Revisión'])
  })
})
