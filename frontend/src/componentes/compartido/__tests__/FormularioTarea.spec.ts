import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import FormularioTarea from '@/componentes/compartido/FormularioTarea.vue'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'

let envoltorio: VueWrapper | null = null

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

function montar(tipo: ValoresFormularioTarea['tipo'] = ''): VueWrapper {
  setActivePinia(createPinia())
  const valores: ValoresFormularioTarea = {
    nombre: '',
    prioridad: '',
    descripcion: '',
    fechaCreacion: '',
    fechaVencimiento: '',
    etiquetas: [],
    asignados: [],
    tipo,
    oportunidad: { codigo: '', descripcion: '', observaciones: '' },
    grupoEstadosId: '',
  }
  envoltorio = mount(FormularioTarea, {
    props: { valores, error: null },
    attachTo: document.body,
  })
  return envoltorio
}

// Contenedor del campo con ese id: el que lleva la clase de obligatorio u opcional.
function contenedor(envoltorio: VueWrapper, id: string) {
  const control = envoltorio.get(`#${id}`)
  const caja = control.element.closest('.campo-obligatorio, .campo-opcional')
  if (!caja) throw new Error(`El campo #${id} no está marcado como obligatorio u opcional`)
  return caja
}

const OBLIGATORIOS = ['tarea-nombre', 'tarea-descripcion', 'fecha-creacion']
const OPCIONALES = [
  'tarea-prioridad',
  'etiquetas',
  'asignados',
  'fecha-vencimiento',
  'tarea-tipo',
  'tarea-grupo-estados',
]

describe('FormularioTarea: campos obligatorios y opcionales', () => {
  it('marca los campos obligatorios en rojo y con asterisco, y los opcionales en verde', () => {
    const formulario = montar()

    for (const id of OBLIGATORIOS) {
      const caja = contenedor(formulario, id)
      expect(caja.classList.contains('campo-obligatorio')).toBe(true)
      expect(formulario.get(`#${id}`).attributes('required')).toBeDefined()
      const asterisco = caja.querySelector('[data-testid="marca-obligatorio"]')
      expect(asterisco?.textContent?.trim()).toBe('*')
      expect(asterisco?.getAttribute('aria-hidden')).toBe('true')
    }
    for (const id of OPCIONALES) {
      const caja = contenedor(formulario, id)
      expect(caja.classList.contains('campo-opcional')).toBe(true)
      expect(caja.querySelector('[data-testid="marca-obligatorio"]')).toBeNull()
    }
  })

  it('explica la leyenda de colores y del asterisco', () => {
    const formulario = montar()

    expect(formulario.get('[data-testid="leyenda-campos"]').text()).toBe(
      'Los campos con * (borde rojo) son obligatorios; los de borde verde, opcionales.',
    )
  })

  it('en una oportunidad, el código es obligatorio y el resto de sus campos opcionales', () => {
    const formulario = montar('oportunidad')

    expect(
      contenedor(formulario, 'oportunidad-codigo').classList.contains('campo-obligatorio'),
    ).toBe(true)
    for (const id of ['oportunidad-descripcion', 'oportunidad-observaciones']) {
      expect(contenedor(formulario, id).classList.contains('campo-opcional')).toBe(true)
    }
  })
})
