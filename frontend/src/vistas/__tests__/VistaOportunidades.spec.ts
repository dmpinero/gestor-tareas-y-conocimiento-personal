import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  lanzarAlta,
  obtenerConfiguracionAlta,
  obtenerEjecucionAlta,
  responderPreguntaAlta,
  type EjecucionAlta,
  type PreguntaAlta,
  type ResumenConfiguracionAlta,
} from '@/api/altaOportunidades'
import { ErrorApi } from '@/api/cliente'
import router from '@/router'
import VistaOportunidades from '../VistaOportunidades.vue'

vi.mock('@/api/altaOportunidades', async (importarOriginal) => {
  const original = await importarOriginal<typeof import('@/api/altaOportunidades')>()
  return {
    ...original,
    obtenerConfiguracionAlta: vi.fn<typeof original.obtenerConfiguracionAlta>(),
    lanzarAlta: vi.fn<typeof original.lanzarAlta>(),
    obtenerEjecucionAlta: vi.fn<typeof original.obtenerEjecucionAlta>(),
    responderPreguntaAlta: vi.fn<typeof original.responderPreguntaAlta>(),
  }
})

const CONFIGURACION: ResumenConfiguracionAlta = {
  valores: {
    perfil: 'Persona Ejemplo',
    cliente: '[CEJ] Cliente Ejemplo S.A.',
    grupo: 'Grupo Ejemplo',
    tipo: 'Tipo Ejemplo',
    segmentacion: 'Segmentación Ejemplo',
    fase: '1 - Fase Ejemplo',
    probabilidad: '50',
    dias_fecha_limite: 7,
    tipo_servicio: 'Servicio Ejemplo',
    lineas_negocio: [{ nombre: 'Línea Ejemplo', porcentaje: '100' }],
    comunidades: [
      { nombre: 'Comunidad A', porcentaje: '80' },
      { nombre: 'Comunidad B', porcentaje: '20' },
    ],
  },
  error: null,
  fecha_limite: '07/02/2026',
  fecha_inicio: '28/02/2026',
  nombre_menu: 'Oportunidades Ejemplo',
}

function ejecucion(cambios: Partial<EjecucionAlta> = {}): EjecucionAlta {
  return {
    id: 'e1',
    prj: 'PRJ-00001',
    estado: 'en_curso',
    terminada: false,
    pasos: ['Abriendo el navegador'],
    pregunta: null,
    mensaje_final: null,
    hay_captura: false,
    ...cambios,
  }
}

function pregunta(cambios: Partial<PreguntaAlta>): PreguntaAlta {
  return { id: 3, tipo: 'guardar', mensaje: '¿Guardar?', detalle: null, opciones: [], ...cambios }
}

let contenedor: VueWrapper | undefined

async function montar(): Promise<VueWrapper> {
  contenedor = mount(VistaOportunidades, { attachTo: document.body })
  await flushPromises()
  return contenedor
}

async function rellenar(vista: VueWrapper, campos: Record<string, string>): Promise<void> {
  for (const [campo, valor] of Object.entries(campos)) {
    await vista.get(`#alta-${campo}`).setValue(valor)
  }
}

function boton(vista: VueWrapper, texto: string) {
  const encontrado = vista.findAll('button').find((b) => b.text() === texto)
  if (!encontrado) throw new Error(`No hay botón "${texto}"`)
  return encontrado
}

beforeEach(() => {
  vi.mocked(obtenerConfiguracionAlta).mockResolvedValue(CONFIGURACION)
  vi.mocked(obtenerEjecucionAlta).mockRejectedValue(new ErrorApi(404, 'Sin altas'))
})

afterEach(() => {
  contenedor?.unmount()
  contenedor = undefined
  vi.clearAllMocks()
})

describe('VistaOportunidades — formulario y resumen', () => {
  it('el título de la página es el nombre del menú de la configuración', async () => {
    const vista = await montar()

    expect(vista.get('h2').text()).toBe('Oportunidades Ejemplo')
  })

  it('muestra lo que se va a crear: nombre, fechas y valores fijos de solo lectura', async () => {
    const vista = await montar()
    await rellenar(vista, { prj: 'PRJ-00001' })

    const resumen = vista.get('[aria-labelledby="titulo-resumen-alta"]').text()
    expect(resumen).toContain('PRJ-00001 + descripción (se buscará en Notion)')
    expect(resumen).toContain('07/02/2026')
    expect(resumen).toContain('28/02/2026')
    expect(resumen).toContain('Persona Ejemplo')
    expect(resumen).toContain('[CEJ] Cliente Ejemplo S.A.')
    expect(resumen).toContain('Comunidad A (80 %)')
    expect(resumen).toContain('Línea Ejemplo (100 %)')

    await rellenar(vista, { descripcion: 'Mi proyecto' })
    expect(vista.get('[aria-labelledby="titulo-resumen-alta"]').text()).toContain(
      'PRJ-00001 Mi proyecto',
    )
  })

  it('valida en línea el código PRJ con el mensaje del script y no lanza el alta', async () => {
    const vista = await montar()
    await rellenar(vista, { prj: 'PRJ-12', duracion: '2', importe: '10000', coste: '8500' })

    await vista.get('form').trigger('submit')

    const campo = vista.get('#alta-prj')
    expect(campo.attributes('aria-invalid')).toBe('true')
    expect(campo.attributes('aria-describedby')?.split(' ')).toContain('error-alta-prj')
    expect(vista.get('#error-alta-prj').text()).toBe(
      'El código debe tener el formato PRJ-XXXXX (5 dígitos).',
    )
    expect(lanzarAlta).not.toHaveBeenCalled()
  })

  it('al salir de un campo obligatorio vacío muestra su error', async () => {
    const vista = await montar()

    await vista.get('#alta-duracion').trigger('blur')

    expect(vista.text()).toContain('La duración es obligatoria.')
    expect(vista.text()).not.toContain('El importe total previsto es obligatorio.')
  })

  it('con la configuración local rota explica el motivo y no deja lanzar', async () => {
    vi.mocked(obtenerConfiguracionAlta).mockResolvedValue({
      valores: null,
      error: 'No existe el archivo de configuración /config/alta_oportunidad.json.',
      fecha_limite: null,
      fecha_inicio: '28/02/2026',
      nombre_menu: 'Alta de oportunidades',
    })
    const vista = await montar()

    expect(vista.get('[role="alert"]').text()).toContain(
      'No existe el archivo de configuración /config/alta_oportunidad.json.',
    )
    expect(boton(vista, 'Crear oportunidad').attributes('disabled')).toBeDefined()
  })

  it('si el servicio no responde, lo dice y no deja lanzar', async () => {
    vi.mocked(obtenerConfiguracionAlta).mockRejectedValue(new ErrorApi(502, 'Bad Gateway'))
    const vista = await montar()

    expect(vista.get('[role="alert"]').text()).toContain('Bad Gateway')
    expect(boton(vista, 'Crear oportunidad').attributes('disabled')).toBeDefined()
  })

  it('con datos válidos lanza el alta y muestra los pasos', async () => {
    vi.mocked(lanzarAlta).mockResolvedValue(ejecucion())
    const vista = await montar()
    await rellenar(vista, { prj: 'PRJ-00001', duracion: '2', importe: '10000', coste: '8500,5' })

    await vista.get('form').trigger('submit')
    await flushPromises()

    expect(lanzarAlta).toHaveBeenCalledWith({
      prj: 'PRJ-00001',
      descripcion: null,
      duracion: 2,
      importe: 10000,
      coste: 8500.5,
    })
    const pasos = vista.get('ol[aria-live="polite"]')
    expect(pasos.text()).toContain('Abriendo el navegador')
    expect(boton(vista, 'Crear oportunidad').attributes('disabled')).toBeDefined()
  })

  it('si ya hay un alta en curso muestra el mensaje de la API', async () => {
    vi.mocked(lanzarAlta).mockRejectedValue(
      new ErrorApi(409, 'Ya hay un alta de oportunidad en curso; espera a que termine.'),
    )
    const vista = await montar()
    await rellenar(vista, { prj: 'PRJ-00001', duracion: '2', importe: '1', coste: '1' })

    await vista.get('form').trigger('submit')
    await flushPromises()

    expect(vista.get('[role="alert"]').text()).toContain(
      'Ya hay un alta de oportunidad en curso; espera a que termine.',
    )
  })
})

describe('VistaOportunidades — preguntas de la automatización', () => {
  it('la pregunta final ofrece Guardar y No guardar, con el resumen, y envía la respuesta', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        pregunta: pregunta({
          id: 7,
          detalle: 'Nombre: PRJ-00001 Mi proyecto',
          opciones: [
            { valor: 'guardar', etiqueta: 'Guardar' },
            { valor: 'no_guardar', etiqueta: 'No guardar' },
          ],
        }),
      }),
    )
    vi.mocked(responderPreguntaAlta).mockResolvedValue(ejecucion())
    const vista = await montar()

    expect(vista.text()).toContain('Nombre: PRJ-00001 Mi proyecto')
    expect(document.activeElement?.id).toBe('titulo-pregunta-alta')
    await boton(vista, 'Guardar').trigger('click')
    await flushPromises()

    expect(responderPreguntaAlta).toHaveBeenCalledWith(7, 'guardar')
  })

  it('"No guardar" envía su respuesta', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        pregunta: pregunta({
          opciones: [
            { valor: 'guardar', etiqueta: 'Guardar' },
            { valor: 'no_guardar', etiqueta: 'No guardar' },
          ],
        }),
      }),
    )
    vi.mocked(responderPreguntaAlta).mockResolvedValue(ejecucion())
    const vista = await montar()

    await boton(vista, 'No guardar').trigger('click')
    await flushPromises()

    expect(responderPreguntaAlta).toHaveBeenCalledWith(3, 'no_guardar')
  })

  it('el aviso de duplicado ofrece crear otra o no', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        pregunta: pregunta({
          tipo: 'duplicado',
          mensaje: 'Ya existe una oportunidad con PRJ-00001. ¿Crear otra igualmente?',
          opciones: [
            { valor: 'si', etiqueta: 'Sí, crear otra' },
            { valor: 'no', etiqueta: 'No' },
          ],
        }),
      }),
    )
    vi.mocked(responderPreguntaAlta).mockResolvedValue(ejecucion())
    const vista = await montar()

    expect(vista.text()).toContain(
      'Ya existe una oportunidad con PRJ-00001. ¿Crear otra igualmente?',
    )
    await boton(vista, 'No').trigger('click')
    await flushPromises()

    expect(responderPreguntaAlta).toHaveBeenCalledWith(3, 'no')
  })

  it('la intervención manual espera a "Continuar"', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        pregunta: pregunta({
          tipo: 'intervencion_manual',
          mensaje: 'Cámbialo tú a mano.',
          opciones: [{ valor: 'continuar', etiqueta: 'Continuar' }],
        }),
      }),
    )
    vi.mocked(responderPreguntaAlta).mockResolvedValue(ejecucion())
    const vista = await montar()

    await boton(vista, 'Continuar').trigger('click')
    await flushPromises()

    expect(responderPreguntaAlta).toHaveBeenCalledWith(3, 'continuar')
  })

  it('la espera del inicio de sesión se explica sin botones de respuesta', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        pregunta: pregunta({ tipo: 'inicio_sesion', mensaje: 'Inicia sesión en la ventana.' }),
      }),
    )
    const vista = await montar()

    const panel = vista.get('[aria-labelledby="titulo-pregunta-alta"]')
    expect(panel.text()).toContain('Inicia sesión en la ventana.')
    expect(panel.findAll('button')).toHaveLength(0)
  })

  it('tras guardar muestra el resultado y la captura', async () => {
    vi.mocked(obtenerEjecucionAlta).mockResolvedValue(
      ejecucion({
        estado: 'guardada',
        terminada: true,
        mensaje_final: 'Oportunidad guardada.',
        hay_captura: true,
      }),
    )
    const vista = await montar()

    expect(vista.text()).toContain('Oportunidad guardada.')
    const imagen = vista.get('img')
    expect(imagen.attributes('src')).toBe(
      '/api/v1/alta-oportunidades/ejecucion/captura?ejecucion=e1',
    )
    expect(imagen.attributes('alt')).toBe('Captura del resultado del alta de PRJ-00001')
    expect(boton(vista, 'Crear oportunidad').attributes('disabled')).toBeUndefined()
  })

  it('sigue el avance consultando el estado cada segundo hasta que termina', async () => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] })
    try {
      vi.mocked(obtenerEjecucionAlta)
        .mockResolvedValueOnce(ejecucion())
        .mockResolvedValueOnce(ejecucion({ pasos: ['Abriendo el navegador', 'Sesión iniciada'] }))
        .mockResolvedValue(
          ejecucion({
            estado: 'no_guardada',
            terminada: true,
            mensaje_final: 'No se ha guardado nada.',
          }),
        )
      const vista = await montar()

      await vi.advanceTimersByTimeAsync(1000)
      await flushPromises()
      expect(vista.text()).toContain('Sesión iniciada')

      await vi.advanceTimersByTimeAsync(1000)
      await flushPromises()
      expect(vista.text()).toContain('No se ha guardado nada.')

      await vi.advanceTimersByTimeAsync(5000)
      expect(obtenerEjecucionAlta).toHaveBeenCalledTimes(3)
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('router', () => {
  it('la ruta /tareas/oportunidades muestra VistaOportunidades', () => {
    const resuelta = router.resolve('/tareas/oportunidades')

    expect(resuelta.name).toBe('oportunidades')
    expect(resuelta.matched[0]?.components?.default).toBe(VistaOportunidades)
  })
})
