import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { createPinia, setActivePinia } from 'pinia'

import { clienteApi } from '@/api/cliente'
import type { Tarea } from '@/api/tipos'
import DetalleTarea from '../DetalleTarea.vue'

// Los comentarios (columna derecha) se cargan desde la API; las subtareas usan
// el almacén de tareas.
vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>().mockResolvedValue([]),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      parchear: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const TAREA_SIN_TIPO: Tarea = {
  id: 2,
  nombre: 'Leer artículo',
  prioridad: null,
  descripcion: 'Artículo\nsobre Vue',
  fecha_creacion: '2026-12-01T17:05:09',
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
}

const TAREA_OPORTUNIDAD: Tarea = {
  id: 1,
  nombre: 'Escribir informe',
  prioridad: 2,
  descripcion: 'Informe trimestral',
  fecha_creacion: '2026-11-10T09:30:00',
  fecha_vencimiento: '2026-11-20T18:00:00',
  etiquetas: ['Backend', 'Urgente'],
  asignados: ['Ana', 'Luis'],
  tipo: 'oportunidad',
  oportunidad: {
    codigo: 'OP-2026-01',
    descripcion: null,
    observaciones: 'Primera línea\nSegunda línea',
  },
  completada: false,
  subtareas: [],
  grupo_estados: null,
  estado: null,
  workflow: null,
}

let contenedor: VueWrapper | null = null

async function montar(tarea: Tarea | null, error: string | null = null): Promise<VueWrapper> {
  const pinia = createPinia()
  setActivePinia(pinia)
  contenedor = mount(DetalleTarea, {
    props: { tarea, error },
    attachTo: document.body,
    global: { plugins: [pinia] },
  })
  await flushPromises()
  return contenedor
}

function modal(): HTMLElement {
  const elemento = document.body.querySelector<HTMLElement>('[role="dialog"]')
  if (!elemento) throw new Error('La modal de detalle no se abrió')
  return elemento
}

// Texto que leen los lectores de pantalla: sin lo marcado como `aria-hidden`
// (p. ej. las iniciales de los avatares). Los elementos de una lista se unen
// con ", ".
function textoAccesible(elemento: Element): string {
  const copia = elemento.cloneNode(true) as Element
  copia.querySelectorAll('[aria-hidden="true"]').forEach((oculto) => oculto.remove())
  const elementos = [...copia.querySelectorAll('li')]
  if (elementos.length > 0) return elementos.map((li) => li.textContent!.trim()).join(', ')
  return copia.textContent!.trim()
}

// Pares término → valor de una lista de descripción.
function paresDe(lista: Element): [string, string][] {
  return [...lista.querySelectorAll(':scope > div')].map((fila) => [
    fila.querySelector('dt')!.textContent!.trim(),
    textoAccesible(fila.querySelector('dd')!),
  ])
}

function listaDe(id: string): Element {
  const lista = modal().querySelector(`dl[data-testid="${id}"]`)
  if (!lista) throw new Error(`No se encontró la lista "${id}"`)
  return lista
}

// Tarjetas con título de los campos de la tarea: título → pares de su lista.
function tarjetasCampos(): [string, [string, string][]][] {
  const campos = modal().querySelector('[data-testid="campos-tarea"]')
  if (!campos) throw new Error('No se encontraron los campos de la tarea')
  return [...campos.querySelectorAll(':scope > section')]
    .filter((tarjeta) => tarjeta.querySelector('dl'))
    .map((tarjeta) => [
      tarjeta.querySelector('h3')!.textContent!.trim(),
      paresDe(tarjeta.querySelector('dl')!),
    ])
}

function titulosTarjetas(): string[] {
  const campos = modal().querySelector('[data-testid="campos-tarea"]')!
  return [...campos.querySelectorAll(':scope > section > h3')].map((h) => h.textContent!.trim())
}

function cabecera(): HTMLElement {
  const elemento = modal().querySelector<HTMLElement>('[data-testid="cabecera-detalle"]')
  if (!elemento) throw new Error('No se encontró la cabecera del detalle')
  return elemento
}

function pildora(id: string): HTMLElement | null {
  return cabecera().querySelector<HTMLElement>(`[data-testid="${id}"]`)
}

function botonCerrar(): HTMLButtonElement {
  const botones = [...modal().querySelectorAll('button')].filter(
    (boton) => boton.textContent?.trim() === 'Cerrar',
  )
  if (botones.length !== 1) throw new Error(`Se esperaba un botón "Cerrar" y hay ${botones.length}`)
  return botones[0] as HTMLButtonElement
}

describe('DetalleTarea', () => {
  beforeEach(() => {
    // Hora fija para que la cuenta atrás sea determinista. Solo se simulan
    // `Date` y el intervalo del reloj: `flushPromises` usa temporizadores reales.
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] })
    vi.setSystemTime(new Date(2026, 10, 18, 14, 44, 40))
  })

  afterEach(() => {
    vi.useRealTimers()
    contenedor?.unmount()
    contenedor = null
    document.body.innerHTML = ''
  })

  it('sin tarea no muestra la modal', async () => {
    await montar(null)

    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
  })

  it('muestra todos los campos de la tarea agrupados en tarjetas, con "—" en los vacíos y sin bloque de oportunidad', async () => {
    await montar(TAREA_SIN_TIPO)

    expect(modal().querySelector('h2')?.textContent?.trim()).toBe('Leer artículo')
    expect(titulosTarjetas()).toEqual([
      'Descripción',
      'Planificación',
      'Personas y etiquetas',
      'Datos generales',
    ])
    expect(tarjetasCampos()).toEqual([
      [
        'Planificación',
        [
          ['Fecha de creación', '01/12/2026 17:05:09'],
          ['Fecha de vencimiento', '—'],
          ['Prioridad', '—'],
          ['Estado', 'Pendiente'],
          ['Grupo de estados', '—'],
          ['Estado del grupo', '—'],
        ],
      ],
      [
        'Personas y etiquetas',
        [
          ['Asignado a', '—'],
          ['Etiquetas', '—'],
        ],
      ],
      [
        'Datos generales',
        [
          ['Nombre', 'Leer artículo'],
          ['Tipo', '—'],
          ['Workflow', '—'],
        ],
      ],
    ])
    // La descripción conserva sus saltos de línea.
    const descripcion = modal().querySelector('[data-testid="descripcion-tarea"]')!
    expect(descripcion.textContent).toBe('Artículo\nsobre Vue')
    expect(descripcion.className).toContain('whitespace-pre-wrap')
    expect(modal().querySelector('[data-testid="campos-oportunidad"]')).toBeNull()
    expect(modal().textContent).not.toContain('Código')
  })

  it('sin descripción muestra "—" en su tarjeta', async () => {
    await montar({ ...TAREA_SIN_TIPO, descripcion: '' })

    expect(modal().querySelector('[data-testid="descripcion-tarea"]')?.textContent).toBe('—')
  })

  it('muestra las personas asignadas con su avatar y las etiquetas como píldoras', async () => {
    await montar(TAREA_OPORTUNIDAD)

    const personas = tarjetasCampos().find(([titulo]) => titulo === 'Personas y etiquetas')![1]
    expect(personas).toEqual([
      ['Asignado a', 'Ana, Luis'],
      ['Etiquetas', 'Backend, Urgente'],
    ])
    const campos = modal().querySelector('[data-testid="campos-tarea"]')!
    expect(
      [...campos.querySelectorAll('[data-testid="avatar-persona"]')].map((a) => a.textContent),
    ).toEqual(['AAna', 'LLuis'])
    const etiquetas = [...campos.querySelectorAll('[data-testid="etiqueta-detalle"]')]
    expect(etiquetas.map((e) => e.textContent?.trim())).toEqual(['Backend', 'Urgente'])
    for (const etiqueta of etiquetas) expect(etiqueta.className).toContain('rounded-full')
  })

  describe('cabecera', () => {
    it('muestra el nombre, las campanas y píldoras de prioridad, estado, tipo y vencimiento', async () => {
      await montar({
        ...TAREA_OPORTUNIDAD,
        // Quedan menos de 48 h: una campana.
        fecha_vencimiento: '2026-11-19T18:00:00',
        grupo_estados: { id: 1, nombre: 'Desarrollo' },
        estado: { id: 11, nombre: 'En curso' },
      })

      expect(cabecera().querySelector('h2')?.textContent?.trim()).toBe('Escribir informe')
      expect(cabecera().querySelector('[data-aviso-vencimiento]')).not.toBeNull()
      expect(pildora('pildora-prioridad')?.textContent?.trim()).toBe('Prioridad 2')
      expect(pildora('pildora-prioridad')?.className).toContain('bg-orange-100')
      expect(pildora('pildora-completado')?.textContent?.trim()).toBe('Pendiente')
      expect(pildora('pildora-estado')?.textContent?.trim()).toBe('En curso')
      expect(pildora('pildora-tipo')?.textContent?.trim()).toBe('Oportunidad')
      expect(pildora('pildora-tipo')?.className).toContain('bg-violet-100')
      const vencimiento = pildora('pildora-vencimiento')!
      expect(vencimiento.querySelector('[data-testid="vencimiento-corto"]')).not.toBeNull()
      expect(vencimiento.querySelector('[data-testid="contador-vencimiento"]')).not.toBeNull()
    })

    it('sin prioridad, tipo, estado del grupo ni vencimiento solo muestra si está pendiente o completada', async () => {
      await montar({ ...TAREA_SIN_TIPO, completada: true })

      expect(pildora('pildora-completado')?.textContent?.trim()).toBe('Completada')
      expect(pildora('pildora-prioridad')).toBeNull()
      expect(pildora('pildora-estado')).toBeNull()
      expect(pildora('pildora-tipo')).toBeNull()
      expect(pildora('pildora-vencimiento')).toBeNull()
    })
  })

  it('muestra "Estado: Completada" si la tarea está completada', async () => {
    await montar({ ...TAREA_SIN_TIPO, completada: true })

    const planificacion = tarjetasCampos().find(([titulo]) => titulo === 'Planificación')![1]
    expect(planificacion).toContainEqual(['Estado', 'Completada'])
    expect(planificacion).not.toContainEqual(['Estado', 'Pendiente'])
  })

  it('muestra el workflow de la tarea', async () => {
    await montar({ ...TAREA_SIN_TIPO, workflow: { id: 3, nombre: 'Altas' } })

    expect(tarjetasCampos().flatMap(([, pares]) => pares)).toContainEqual(['Workflow', 'Altas'])
  })

  it('muestra el grupo de estados de la tarea y su estado en el grupo', async () => {
    await montar({
      ...TAREA_SIN_TIPO,
      grupo_estados: { id: 1, nombre: 'Desarrollo' },
      estado: { id: 11, nombre: 'En curso' },
    })

    const pares = tarjetasCampos().flatMap(([, pares]) => pares)
    expect(pares).toContainEqual(['Grupo de estados', 'Desarrollo'])
    expect(pares).toContainEqual(['Estado del grupo', 'En curso'])
    // El estado de completado sigue aparte.
    expect(pares).toContainEqual(['Estado', 'Pendiente'])
  })

  it('con tipo Oportunidad muestra su sección con todos sus campos', async () => {
    await montar(TAREA_OPORTUNIDAD)

    expect(tarjetasCampos().flatMap(([, pares]) => pares)).toEqual([
      ['Fecha de creación', '10/11/2026 09:30:00'],
      ['Fecha de vencimiento', '20/11/2026 18:00:00'],
      ['Prioridad', '2'],
      ['Estado', 'Pendiente'],
      ['Grupo de estados', '—'],
      ['Estado del grupo', '—'],
      ['Asignado a', 'Ana, Luis'],
      ['Etiquetas', 'Backend, Urgente'],
      ['Nombre', 'Escribir informe'],
      ['Tipo', 'Oportunidad'],
      ['Workflow', '—'],
    ])
    expect(modal().querySelector('[data-testid="descripcion-tarea"]')?.textContent).toBe(
      'Informe trimestral',
    )
    const seccion = listaDe('campos-oportunidad')
    expect([...modal().querySelectorAll('h3')].map((h) => h.textContent?.trim())).toContain(
      'Oportunidad',
    )
    expect(paresDe(seccion)).toEqual([
      ['Código', 'OP-2026-01'],
      ['Descripción de la oportunidad', '—'],
      ['Observaciones', 'Primera línea\nSegunda línea'],
    ])
    // Los textos largos conservan sus saltos de línea.
    const observaciones = [...seccion.querySelectorAll('dd')][2]!
    expect(observaciones.className).toContain('whitespace-pre-wrap')
  })

  it('en la cabecera, junto al vencimiento, muestra la cuenta atrás, que avanza cada segundo', async () => {
    await montar(TAREA_OPORTUNIDAD)

    // Una sola cuenta atrás: la de la cabecera.
    expect(modal().querySelectorAll('[data-testid="contador-vencimiento"]')).toHaveLength(1)
    const contador = pildora('pildora-vencimiento')!.querySelector(
      '[data-testid="contador-vencimiento"]',
    )
    expect(contador?.textContent?.trim()).toBe('Vence en 2 d 03 h 15 min 20 s')
    expect(contador?.getAttribute('role')).toBe('timer')

    vi.advanceTimersByTime(1000)
    await flushPromises()

    expect(contador?.textContent?.trim()).toBe('Vence en 2 d 03 h 15 min 19 s')
  })

  it('con el vencimiento pasado muestra cuánto hace que venció en rojo', async () => {
    vi.setSystemTime(new Date(2026, 10, 21, 20, 5, 59))
    await montar(TAREA_OPORTUNIDAD)

    const contador = modal().querySelector('[data-testid="contador-vencimiento"]')
    expect(contador?.textContent?.trim()).toBe('Vencida hace 1 d 02 h 05 min')
    expect(contador?.classList.contains('text-destructive')).toBe(true)
  })

  it('sin fecha de vencimiento no muestra cuenta atrás', async () => {
    await montar(TAREA_SIN_TIPO)

    expect(modal().querySelector('[data-testid="contador-vencimiento"]')).toBeNull()
  })

  it('ocupa el 90 % del ancho y del alto del viewport con scroll interno', async () => {
    await montar(TAREA_OPORTUNIDAD)

    const clases = modal().className.split(/\s+/)
    expect(clases).toEqual(expect.arrayContaining(['w-[90vw]', 'max-w-none', 'h-[90vh]']))
    expect(clases).not.toContain('max-w-lg')
    const zonaScroll = modal().querySelector('[data-testid="detalle-contenido"]')
    expect(zonaScroll?.className).toContain('overflow-y-auto')
  })

  it('el botón "Cerrar" pide cerrar la modal', async () => {
    const envoltorio = await montar(TAREA_SIN_TIPO)

    botonCerrar().click()
    await flushPromises()

    expect(envoltorio.emitted('cerrar')).toHaveLength(1)
  })

  it('la tecla Escape pide cerrar la modal', async () => {
    const envoltorio = await montar(TAREA_SIN_TIPO)

    modal().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))
    await flushPromises()

    expect(envoltorio.emitted('cerrar')).toHaveLength(1)
  })

  describe('sin pasos del workflow', () => {
    it('una oportunidad no muestra pasos del workflow: sus pasos son subtareas', async () => {
      await montar(TAREA_OPORTUNIDAD)

      const titulos = [...modal().querySelectorAll('h3, h4')].map((h) => h.textContent?.trim())
      expect(titulos).not.toContain('Pasos del workflow')
      expect(modal().querySelector('[data-testid="pasos-oportunidad"]')).toBeNull()
      expect(modal().textContent).not.toContain('Esta oportunidad no tiene pasos.')
      expect(modal().querySelector('[role="checkbox"]')).toBeNull()
    })

    it('muestra el error recibido dentro de la modal', async () => {
      await montar(TAREA_OPORTUNIDAD, 'Subtarea no encontrada')

      expect(modal().querySelector('[role="alert"]')?.textContent?.trim()).toBe(
        'Subtarea no encontrada',
      )
    })

    it('sin error no muestra ninguna alerta', async () => {
      await montar(TAREA_OPORTUNIDAD)

      expect(modal().querySelector('[role="alert"]')).toBeNull()
    })
  })

  describe('eliminar la tarea', () => {
    it('el pie tiene un botón "Eliminar la tarea X" con icono que pide eliminarla', async () => {
      const envoltorio = await montar(TAREA_OPORTUNIDAD)

      const boton = modal().querySelector<HTMLButtonElement>(
        '[data-slot="dialog-footer"] button[aria-label="Eliminar la tarea Escribir informe"]',
      )
      if (!boton) throw new Error('No se encontró el botón de eliminar la tarea')
      expect(boton.querySelector('svg')).not.toBeNull()
      boton.click()
      await flushPromises()

      expect(envoltorio.emitted('eliminar')).toEqual([[]])
      // Solo lo pide: la confirmación y el cierre son cosa de quien la usa.
      expect(envoltorio.emitted('cerrar')).toBeUndefined()
    })
  })

  describe('subtareas y comentarios', () => {
    it('muestra las subtareas a la izquierda y los comentarios de la tarea a la derecha', async () => {
      vi.mocked(clienteApi.obtener).mockResolvedValue([
        { id: 1, texto: 'Primer comentario', creado: new Date(2026, 3, 1, 17, 30).toISOString() },
      ])

      await montar(TAREA_SIN_TIPO)

      const dialogo = document.body.querySelector('[role="dialog"]')!
      const contenido = dialogo.querySelector('[data-testid="detalle-contenido"]')!
      const titulos = [...contenido.querySelectorAll('h3')].map((h) => h.textContent?.trim())
      expect(titulos).toContain('Subtareas')
      const comentarios = dialogo.querySelector('[data-testid="columna-comentarios"]')!
      expect(comentarios.textContent).toContain('Comentarios')
      expect(comentarios.textContent).toContain('Primer comentario')
      expect(clienteApi.obtener).toHaveBeenCalledWith(`/tareas/${TAREA_SIN_TIPO.id}/comentarios`)
      // La columna de comentarios va después del contenido (a la derecha en pantallas anchas).
      expect(
        contenido.compareDocumentPosition(comentarios) & Node.DOCUMENT_POSITION_FOLLOWING,
      ).toBeTruthy()
    })
  })

  describe('edición', () => {
    it('"Editar" emite `editar` y no cambia nada por sí solo', async () => {
      const envoltorio = await montar(TAREA_SIN_TIPO)

      const editar = [...modal().querySelectorAll('button')].find(
        (boton) => boton.textContent?.trim() === 'Editar',
      )!
      expect(editar.getAttribute('aria-label')).toBe('Editar la tarea Leer artículo')
      editar.click()
      await flushPromises()

      expect(envoltorio.emitted('editar')).toHaveLength(1)
      expect(modal().querySelector('[data-testid="campos-tarea"]')).not.toBeNull()
    })

    it('con `editando` muestra el slot `edicion` en lugar de los datos y oculta "Editar"', async () => {
      const pinia = createPinia()
      setActivePinia(pinia)
      contenedor = mount(DetalleTarea, {
        props: { tarea: TAREA_SIN_TIPO, editando: true },
        slots: { edicion: '<form data-testid="formulario-de-prueba" />' },
        attachTo: document.body,
        global: { plugins: [pinia] },
      })
      await flushPromises()

      expect(modal().querySelector('[data-testid="formulario-de-prueba"]')).not.toBeNull()
      expect(modal().querySelector('[data-testid="campos-tarea"]')).toBeNull()
      expect(modal().querySelector('[data-testid="columna-comentarios"]')).not.toBeNull()
      expect(
        [...modal().querySelectorAll('button')].some((b) => b.textContent?.trim() === 'Editar'),
      ).toBe(false)
    })
  })
})
