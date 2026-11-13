import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'

import type { Workflow } from '@/api/tipos'
import FormularioTarea from '@/componentes/compartido/FormularioTarea.vue'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'
import { useTiendaWorkflows } from '@/stores/workflows'

let envoltorio: VueWrapper | null = null
// Valores que recibe el formulario montado, para comprobar lo que escribe.
let valoresMontados: ValoresFormularioTarea | null = null

afterEach(() => {
  envoltorio?.unmount()
  envoltorio = null
  document.body.innerHTML = ''
})

const WORKFLOWS: Workflow[] = [
  { id: 1, nombre: 'Altas', pasos: [] },
  { id: 2, nombre: 'Workflow Oportunidades', pasos: [{ id: 10, numero: 1, nombre: 'Contacto' }] },
]

function montar(
  tipo: ValoresFormularioTarea['tipo'] = '',
  opciones: { alta?: boolean; workflowId?: number | ''; workflows?: Workflow[] } = {},
): VueWrapper {
  setActivePinia(createPinia())
  useTiendaWorkflows().workflows = opciones.workflows ?? WORKFLOWS
  const valores: ValoresFormularioTarea = reactive({
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
    workflowId: opciones.workflowId ?? '',
  })
  valoresMontados = valores
  envoltorio = mount(FormularioTarea, {
    props: { valores, error: null, alta: opciones.alta },
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
  'tarea-workflow',
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

describe('FormularioTarea: workflow', () => {
  function selector(formulario: VueWrapper): HTMLSelectElement {
    return formulario.get('select#tarea-workflow').element as HTMLSelectElement
  }

  function valores(): ValoresFormularioTarea {
    if (!valoresMontados) throw new Error('No hay formulario montado')
    return valoresMontados
  }

  it('ofrece "Sin workflow" y los workflows de Ajustes en un campo "Workflow"', () => {
    const formulario = montar()

    expect(formulario.get('label[for="tarea-workflow"]').text()).toBe('Workflow')
    expect([...selector(formulario).options].map((opcion) => opcion.text.trim())).toEqual([
      'Sin workflow',
      'Altas',
      'Workflow Oportunidades',
    ])
    expect(selector(formulario).value).toBe('')
  })

  it('elegir un workflow guarda su id en los valores', async () => {
    const formulario = montar()

    await formulario.get('select#tarea-workflow').setValue('1')

    expect(valores().workflowId).toBe(1)
  })

  it('en el alta, al elegir el tipo Oportunidad sin workflow preselecciona "Workflow Oportunidades"', async () => {
    const formulario = montar('', { alta: true })

    await formulario.get('select#tarea-tipo').setValue('oportunidad')
    await flushPromises()

    expect(valores().workflowId).toBe(2)
    expect(selector(formulario).value).toBe('2')
  })

  it('en el alta no cambia el workflow ya elegido al elegir el tipo Oportunidad', async () => {
    const formulario = montar('', { alta: true, workflowId: 1 })

    await formulario.get('select#tarea-tipo').setValue('oportunidad')
    await flushPromises()

    expect(valores().workflowId).toBe(1)
  })

  it('en el alta no preselecciona nada si no existe "Workflow Oportunidades"', async () => {
    const formulario = montar('', { alta: true, workflows: [WORKFLOWS[0]!] })

    await formulario.get('select#tarea-tipo').setValue('oportunidad')
    await flushPromises()

    expect(valores().workflowId).toBe('')
  })

  it('en la edición no preselecciona el workflow al elegir el tipo Oportunidad', async () => {
    const formulario = montar('', { alta: false })

    await formulario.get('select#tarea-tipo').setValue('oportunidad')
    await flushPromises()

    expect(valores().workflowId).toBe('')
  })
})
