import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  lanzarAltaAxasMs3,
  obtenerConfiguracionAlta,
  obtenerConfiguracionAxasMs3,
  obtenerEjecucionAlta,
  type ResumenConfiguracionAxasMs3,
} from '@/api/altaOportunidades'
import { clienteApi, ErrorApi } from '@/api/cliente'
import router from '@/router'
import VistaOportunidades from '../VistaOportunidades.vue'

vi.mock('@/api/altaOportunidades', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/altaOportunidades')>()
  return {
    ...original,
    obtenerConfiguracionAlta: vi.fn<typeof original.obtenerConfiguracionAlta>(),
    obtenerConfiguracionAxasMs3: vi.fn<typeof original.obtenerConfiguracionAxasMs3>(),
    lanzarAltaAxasMs3: vi.fn<typeof original.lanzarAltaAxasMs3>(),
    obtenerEjecucionAlta: vi.fn<typeof original.obtenerEjecucionAlta>(),
  }
})

vi.mock('@/api/cliente', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/cliente')>()
  return {
    ...original,
    clienteApi: {
      obtener: vi.fn<(...args: unknown[]) => unknown>(),
      crear: vi.fn<(...args: unknown[]) => unknown>(),
      actualizar: vi.fn<(...args: unknown[]) => unknown>(),
      parchear: vi.fn<(...args: unknown[]) => unknown>(),
      eliminar: vi.fn<(...args: unknown[]) => unknown>(),
    },
  }
})

const CONFIGURACION: ResumenConfiguracionAxasMs3 = {
  valores: {
    perfil: 'Responsable Ejemplo',
    cliente: '[CEJ] Cliente Ejemplo S.A.',
    grupo: 'Grupo Ejemplo',
    tipo: 'Tipo Ejemplo',
    segmentacion: 'Segmentación Ejemplo',
    fase: '1 - Fase Ejemplo',
    probabilidad: '50',
    dias_fecha_limite: 7,
    tipo_servicio: 'Servicio MS3 Ejemplo',
    lineas_negocio: [{ nombre: 'Línea Ejemplo', porcentaje: '100' }],
    comunidades: [
      { nombre: 'Comunidad A', porcentaje: '80' },
      { nombre: 'Comunidad B', porcentaje: '20' },
    ],
    responsable_operaciones: 'Operaciones Ejemplo',
    responsable_tecnico: 'Técnico Ejemplo',
    area_ms3: 'Área Ejemplo',
  },
  error: null,
  fecha_limite: '07/02/2026',
  fecha_inicio: '28/02/2026',
  nombre_menu: 'Oportunidades AXAS MS3',
}

const CODIGOS = [
  { id: 1, nombre: 'AXAS0024' },
  { id: 2, nombre: 'AXAS0025' },
]

let contenedor: VueWrapper | undefined

async function montar(): Promise<VueWrapper> {
  setActivePinia(createPinia())
  contenedor = mount(VistaOportunidades, {
    props: { variante: 'axas-ms3' },
    attachTo: document.body,
  })
  await flushPromises()
  return contenedor
}

function combobox(vista: VueWrapper) {
  return vista.get('#alta-codigo')
}

function opciones(): string[] {
  return [...document.querySelectorAll('[role="option"]')].map((o) => o.textContent!.trim())
}

async function elegir(texto: string): Promise<void> {
  const opcion = [...document.querySelectorAll<HTMLElement>('[role="option"]')].find(
    (o) => o.textContent!.trim() === texto,
  )
  if (!opcion) throw new Error(`No hay opción "${texto}"`)
  opcion.click()
  await flushPromises()
}

function nombrePrevisto(vista: VueWrapper): string {
  const dt = vista.findAll('dt').find((d) => d.text() === 'Nombre')!
  return (dt.element.nextElementSibling as HTMLElement).textContent!.trim()
}

beforeEach(() => {
  vi.mocked(obtenerConfiguracionAxasMs3).mockResolvedValue(CONFIGURACION)
  vi.mocked(obtenerEjecucionAlta).mockRejectedValue(new ErrorApi(404, 'Sin altas'))
  vi.mocked(clienteApi.obtener).mockResolvedValue(structuredClone(CODIGOS))
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = undefined
  vi.clearAllMocks()
})

describe('VistaOportunidades — AXAS MS3', () => {
  it('usa la configuración de AXAS MS3 y muestra sus valores fijos', async () => {
    const vista = await montar()

    expect(vista.get('h2').text()).toBe('Oportunidades AXAS MS3')
    const texto = vista.get('[aria-labelledby="titulo-resumen-alta"]').text()
    expect(texto).toContain('Operaciones Ejemplo')
    expect(texto).toContain('Técnico Ejemplo')
    expect(texto).toContain('Área Ejemplo')
    expect(vista.find('#alta-prj').exists()).toBe(false)
  })

  it('el combobox lista los códigos al abrirlo y filtra al escribir', async () => {
    const vista = await montar()
    expect(clienteApi.obtener).toHaveBeenCalledWith('/codigos-servicio')

    await combobox(vista).trigger('focus')
    expect(opciones()).toEqual(['AXAS0024', 'AXAS0025'])

    await combobox(vista).setValue('25')
    expect(opciones()).toEqual(['AXAS0025', 'Crear "25"'])
  })

  it('al elegir un código el nombre previsto usa sus 2 últimos caracteres y la descripción', async () => {
    const vista = await montar()
    await combobox(vista).trigger('focus')
    await elegir('AXAS0024')
    await vista.get('#alta-descripcion').setValue('Migración portal')

    expect((combobox(vista).element as HTMLInputElement).value).toBe('AXAS0024')
    expect(nombrePrevisto(vista)).toBe('AXAS-MS3-EV24-Migración portal')
  })

  it('crear un código nuevo lo da de alta en el catálogo y lo deja elegido', async () => {
    vi.mocked(clienteApi.crear).mockResolvedValue({ id: 3, nombre: 'AXAS0026' })
    const vista = await montar()

    await combobox(vista).setValue('AXAS0026')
    await elegir('Crear "AXAS0026"')

    expect(clienteApi.crear).toHaveBeenCalledWith('/codigos-servicio', { nombre: 'AXAS0026' })
    expect((combobox(vista).element as HTMLInputElement).value).toBe('AXAS0026')
    await combobox(vista).setValue('')
    await combobox(vista).trigger('focus')
    expect(opciones()).toContain('AXAS0026')
  })

  it('no ofrece crear un código no válido y explica por qué', async () => {
    const vista = await montar()

    await combobox(vista).setValue('AX AS')

    expect(opciones()).not.toContain('Crear "AX AS"')
    expect(vista.text()).toContain('El código de servicio no puede contener espacios.')
  })

  it('exige código y descripción antes de lanzar', async () => {
    const vista = await montar()

    await vista.get('form').trigger('submit')

    expect(vista.text()).toContain('Elige o crea un código de servicio.')
    expect(vista.text()).toContain('La descripción es obligatoria.')
    expect(lanzarAltaAxasMs3).not.toHaveBeenCalled()
  })

  it('con datos válidos lanza el alta de AXAS MS3 con el código elegido', async () => {
    vi.mocked(lanzarAltaAxasMs3).mockResolvedValue({
      id: 'e1',
      prj: 'AXAS-MS3-EV24-Migración portal',
      estado: 'en_curso',
      terminada: false,
      pasos: ['Abriendo el navegador'],
      pregunta: null,
      mensaje_final: null,
      hay_captura: false,
    })
    const vista = await montar()
    await combobox(vista).trigger('focus')
    await elegir('AXAS0024')
    await vista.get('#alta-descripcion').setValue('Migración portal')
    await vista.get('#alta-duracion').setValue('6')
    await vista.get('#alta-importe').setValue('1000')
    await vista.get('#alta-coste').setValue('800')

    await vista.get('form').trigger('submit')
    await flushPromises()

    expect(lanzarAltaAxasMs3).toHaveBeenCalledWith({
      codigo_servicio: 'AXAS0024',
      descripcion: 'Migración portal',
      duracion: 6,
      importe: 1000,
      coste: 800,
    })
    expect(vista.text()).toContain('Avance del alta de AXAS-MS3-EV24-Migración portal')
  })
})

describe('VistaOportunidades — cambio de variante', () => {
  it('al pasar de ANES a AXAS MS3 con la vista montada recarga la configuración y vacía el formulario', async () => {
    vi.mocked(obtenerConfiguracionAlta).mockResolvedValue({
      ...CONFIGURACION,
      valores: null,
      nombre_menu: 'Oportunidades ANES',
    })
    setActivePinia(createPinia())
    contenedor = mount(VistaOportunidades, { props: { variante: 'anes' }, attachTo: document.body })
    await flushPromises()
    await contenedor.get('#alta-descripcion').setValue('Algo de ANES')
    expect(contenedor.get('h2').text()).toBe('Oportunidades ANES')

    await contenedor.setProps({ variante: 'axas-ms3' })
    await flushPromises()

    expect(contenedor.get('h2').text()).toBe('Oportunidades AXAS MS3')
    expect(contenedor.find('#alta-prj').exists()).toBe(false)
    expect(contenedor.find('#alta-codigo').exists()).toBe(true)
    expect((contenedor.get('#alta-descripcion').element as HTMLInputElement).value).toBe('')
  })
})

describe('VistaOportunidades — respuesta tardía al cambiar de variante', () => {
  it('si la configuración de ANES llega después de pasar a AXAS MS3, se ignora', async () => {
    let resolverAnes: (valor: ResumenConfiguracionAxasMs3) => void = () => {}
    vi.mocked(obtenerConfiguracionAlta).mockReturnValue(
      new Promise((resolver) => {
        resolverAnes = resolver
      }),
    )
    setActivePinia(createPinia())
    contenedor = mount(VistaOportunidades, { props: { variante: 'anes' }, attachTo: document.body })
    await flushPromises()

    await contenedor.setProps({ variante: 'axas-ms3' })
    await flushPromises()
    resolverAnes({ ...CONFIGURACION, valores: null, nombre_menu: 'Oportunidades ANES' })
    await flushPromises()

    expect(contenedor.get('h2').text()).toBe('Oportunidades AXAS MS3')
    expect(contenedor.text()).toContain('Área Ejemplo')
  })
})

describe('router', () => {
  it('la ruta /oportunidades/axas-ms3 muestra el alta de AXAS MS3', () => {
    const ruta = router.resolve('/oportunidades/axas-ms3')
    expect(ruta.name).toBe('oportunidades-axas-ms3')
    expect(ruta.matched[0]!.components!.default).toBe(VistaOportunidades)
    expect(ruta.matched[0]!.props).toEqual({ default: { variante: 'axas-ms3' } })
  })
})
