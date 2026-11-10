import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, ref } from 'vue'

import SelectorFechaHora from '@/componentes/compartido/SelectorFechaHora.vue'
import { Sheet, SheetContent, SheetTitle } from '@/componentes/ui/sheet'

let envoltorios: VueWrapper[] = []

function montar(propiedades: Record<string, unknown> = {}) {
  const envoltorio = mount(SelectorFechaHora, {
    props: { id: 'fecha', modelValue: '', ...propiedades },
    attachTo: document.body,
  })
  envoltorios.push(envoltorio)
  return envoltorio
}

function ultimoValorEmitido(envoltorio: VueWrapper): unknown {
  const emitidos = envoltorio.emitted('update:modelValue') ?? []
  return emitidos[emitidos.length - 1]?.[0]
}

function buscarEnDocumento<T extends Element = HTMLElement>(selector: string): T | null {
  return document.body.querySelector<T>(selector)
}

function popover(): HTMLElement | null {
  return buscarEnDocumento('[data-slot="popover-content"]')
}

async function abrirCalendario(envoltorio: VueWrapper) {
  await envoltorio.get('button[aria-label^="Abrir calendario"]').trigger('click')
  await flushPromises()
}

function dia(numero: number): HTMLElement {
  const celdas = Array.from(
    document.body.querySelectorAll<HTMLElement>('[data-slot="calendar-cell-trigger"]'),
  ).filter(
    (celda) =>
      celda.textContent?.trim() === String(numero) && !celda.hasAttribute('data-outside-view'),
  )
  const celda = celdas[0]
  if (!celda) throw new Error(`No se encuentra el día ${numero}`)
  return celda
}

function campoTiempo(etiqueta: string): HTMLInputElement {
  const etiquetaHtml = Array.from(document.body.querySelectorAll('label')).find(
    (elemento) => elemento.textContent?.trim() === etiqueta,
  )
  const id = etiquetaHtml?.getAttribute('for')
  const campo = id ? document.getElementById(id) : null
  if (!(campo instanceof HTMLInputElement)) throw new Error(`No se encuentra ${etiqueta}`)
  return campo
}

async function escribirEn(campo: HTMLInputElement, valor: string) {
  campo.value = valor
  campo.dispatchEvent(new Event('input'))
  await flushPromises()
}

function encabezado(): string {
  return buscarEnDocumento('[data-slot="calendar-heading"]')?.textContent?.trim() ?? ''
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 0, 5, 9, 3, 7))
})

afterEach(() => {
  for (const envoltorio of envoltorios) envoltorio.unmount()
  envoltorios = []
  vi.useRealTimers()
  document.body.innerHTML = ''
})

describe('SelectorFechaHora', () => {
  it('muestra el v-model en el campo con el formato, el patrón y el id indicados', () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07', required: true })

    const campo = envoltorio.get('input#fecha')
    expect((campo.element as HTMLInputElement).value).toBe('05/01/2026 09:03:07')
    expect(campo.attributes('placeholder')).toBe('dd/mm/aaaa hh:mm:ss')
    expect(campo.attributes('pattern')).toBe('\\d{2}/\\d{2}/\\d{4} \\d{2}:\\d{2}:\\d{2}')
    expect(campo.attributes('required')).toBeDefined()
  })

  it('escribir en el campo emite el texto tal cual', async () => {
    const envoltorio = montar()

    await envoltorio.get('input#fecha').setValue('10/02/2026 08:00:00')
    await flushPromises()

    expect(ultimoValorEmitido(envoltorio)).toBe('10/02/2026 08:00:00')
  })

  it('el botón abre el calendario con nombre accesible basado en la etiqueta', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07', etiqueta: 'Fecha de creación' })

    expect(popover()).toBeNull()
    const boton = envoltorio.get('button[aria-label="Abrir calendario de Fecha de creación"]')
    await boton.trigger('click')
    await flushPromises()

    expect(popover()).not.toBeNull()
    expect(encabezado().toLowerCase()).toContain('enero')
    expect(encabezado()).toContain('2026')
  })

  it('sin etiqueta, el botón se llama "Abrir calendario"', () => {
    const envoltorio = montar()

    expect(envoltorio.find('button[aria-label="Abrir calendario"]').exists()).toBe(true)
  })

  it('la semana empieza en lunes y los textos están en español', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    const cabeceras = Array.from(
      document.body.querySelectorAll('[data-slot="calendar-head-cell"]'),
    ).map((celda) => celda.textContent?.trim())
    expect(cabeceras[0]).toBe('lun')
    expect(cabeceras[6]).toBe('dom')
    // El 1 de enero de 2026 es jueves: la primera fila arranca el lunes 29 de diciembre.
    const primerDia = document.body.querySelector('[data-slot="calendar-cell-trigger"]')
    expect(primerDia?.textContent?.trim()).toBe('29')
  })

  it('elegir un día conserva la hora actual del campo y emite dd/mm/aaaa hh:mm:ss', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    dia(20).click()
    await flushPromises()

    expect(ultimoValorEmitido(envoltorio)).toBe('20/01/2026 09:03:07')
    // Sigue abierto para poder ajustar la hora.
    expect(popover()).not.toBeNull()
  })

  it('elegir un día con el campo vacío usa 00:00:00 y el mes actual', async () => {
    const envoltorio = montar()
    await abrirCalendario(envoltorio)
    expect(encabezado().toLowerCase()).toContain('enero')

    dia(15).click()
    await flushPromises()

    expect(ultimoValorEmitido(envoltorio)).toBe('15/01/2026 00:00:00')
  })

  it('cambiar hora, minutos y segundos emite el valor actualizado', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    expect(campoTiempo('Hora').value).toBe('9')
    await escribirEn(campoTiempo('Hora'), '18')
    expect(ultimoValorEmitido(envoltorio)).toBe('05/01/2026 18:03:07')

    await envoltorio.setProps({ modelValue: '05/01/2026 18:03:07' })
    await escribirEn(campoTiempo('Minutos'), '45')
    expect(ultimoValorEmitido(envoltorio)).toBe('05/01/2026 18:45:07')

    await envoltorio.setProps({ modelValue: '05/01/2026 18:45:07' })
    await escribirEn(campoTiempo('Segundos'), '59')
    expect(ultimoValorEmitido(envoltorio)).toBe('05/01/2026 18:45:59')
  })

  it('una hora fuera de rango se ajusta al límite', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    await escribirEn(campoTiempo('Hora'), '30')

    expect(ultimoValorEmitido(envoltorio)).toBe('05/01/2026 23:03:07')
  })

  it('escribir una fecha válida lleva el calendario a su mes', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)
    expect(encabezado().toLowerCase()).toContain('enero')

    await envoltorio.setProps({ modelValue: '14/03/2027 10:00:00' })
    await flushPromises()

    expect(encabezado().toLowerCase()).toContain('marzo')
    expect(encabezado()).toContain('2027')
    expect(dia(14).hasAttribute('data-selected')).toBe(true)
  })

  it('un valor no válido no rompe ni mueve el calendario', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    await envoltorio.setProps({ modelValue: '31/02/2026 10:00:00' })
    await flushPromises()
    expect(encabezado().toLowerCase()).toContain('enero')

    await envoltorio.setProps({ modelValue: 'texto' })
    await flushPromises()
    expect(encabezado().toLowerCase()).toContain('enero')
    expect((envoltorio.get('input#fecha').element as HTMLInputElement).value).toBe('texto')
  })

  it('"Aceptar" cierra el calendario', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    const aceptar = Array.from(document.body.querySelectorAll('button')).find(
      (boton) => boton.textContent?.trim() === 'Aceptar',
    )
    aceptar?.click()
    await flushPromises()

    expect(popover()).toBeNull()
  })

  it('Escape cierra el calendario', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })
    await abrirCalendario(envoltorio)

    document.activeElement?.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
    )
    await flushPromises()

    expect(popover()).toBeNull()
  })

  it('anulable muestra "Borrar fecha", que deja el campo vacío', async () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07', anulable: true })

    await envoltorio.get('button[aria-label="Borrar fecha"]').trigger('click')
    await flushPromises()

    expect(ultimoValorEmitido(envoltorio)).toBe('')
  })

  it('sin anulable no hay botón "Borrar fecha"', () => {
    const envoltorio = montar({ modelValue: '05/01/2026 09:03:07' })

    expect(envoltorio.find('button[aria-label="Borrar fecha"]').exists()).toBe(false)
  })

  it('funciona dentro de un Sheet: el calendario se abre y elegir un día no cierra el panel', async () => {
    const valor = ref('05/01/2026 09:03:07')
    const conPanel = defineComponent({
      setup() {
        return () =>
          h(Sheet, { open: true }, () =>
            h(SheetContent, null, () => [
              h(SheetTitle, null, () => 'Panel'),
              h(SelectorFechaHora, {
                id: 'fecha',
                etiqueta: 'Fecha de creación',
                modelValue: valor.value,
                'onUpdate:modelValue': (nuevo: string) => {
                  valor.value = nuevo
                },
              }),
            ]),
          )
      },
    })
    envoltorios.push(mount(conPanel, { attachTo: document.body }))
    await flushPromises()

    const boton = buscarEnDocumento<HTMLButtonElement>(
      'button[aria-label="Abrir calendario de Fecha de creación"]',
    )
    expect(boton).not.toBeNull()
    boton?.click()
    await flushPromises()

    const contenido = popover()
    expect(contenido).not.toBeNull()
    // El popover está fuera del diálogo (teletransportado) pero sigue siendo clicable.
    expect(contenido?.style.pointerEvents).not.toBe('none')

    const celda = dia(20)
    celda.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    celda.click()
    await flushPromises()

    expect(valor.value).toBe('20/01/2026 09:03:07')
    expect(buscarEnDocumento('[data-slot="sheet-content"]')).not.toBeNull()

    await escribirEn(campoTiempo('Hora'), '11')
    expect(valor.value).toBe('20/01/2026 11:03:07')
    expect(buscarEnDocumento('[data-slot="sheet-content"]')).not.toBeNull()
  })
})
