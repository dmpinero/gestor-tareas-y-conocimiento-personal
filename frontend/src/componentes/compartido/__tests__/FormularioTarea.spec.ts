import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { reactive } from 'vue'

import type { Workflow } from '@/api/tipos'
import FormularioTarea from '@/componentes/compartido/FormularioTarea.vue'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'
import { useTiendaTareas } from '@/stores/tareas'
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
  {
    id: 2,
    nombre: 'Workflow Oportunidades',
    pasos: [{ id: 10, numero: 1, nombre: 'Contacto', comentarios: 0 }],
  },
]

function montar(
  tipo: ValoresFormularioTarea['tipo'] = '',
  opciones: {
    alta?: boolean
    workflowId?: number | ''
    workflows?: Workflow[]
    subestado?: string
  } = {},
): VueWrapper {
  setActivePinia(createPinia())
  useTiendaWorkflows().workflows = opciones.workflows ?? WORKFLOWS
  useTiendaTareas().subestados = ['Bloqueado', 'En pausa']
  const valores: ValoresFormularioTarea = reactive({
    nombre: '',
    prioridad: '',
    descripcion: '',
    fechaCreacion: '',
    fechaVencimiento: '',
    etiquetas: [],
    asignados: [],
    subestado: opciones.subestado ?? '',
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
  'subestado',
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

describe('FormularioTarea: subestado', () => {
  function valores(): ValoresFormularioTarea {
    if (!valoresMontados) throw new Error('No hay formulario montado')
    return valoresMontados
  }

  async function escribirSubestado(formulario: VueWrapper, texto: string): Promise<void> {
    await formulario.get('input#subestado').setValue(texto)
    await flushPromises()
  }

  it('tiene un campo "Subestado" que sugiere los subestados del catálogo', async () => {
    const formulario = montar()

    expect(formulario.get('label[for="subestado"]').text()).toBe('Subestado')
    await escribirSubestado(formulario, 'blo')

    expect(formulario.findAll('[role="option"]').map((opcion) => opcion.text())).toEqual([
      'Bloqueado',
      'Crear subestado "blo"',
    ])
  })

  it('elegir un subestado lo guarda en los valores y otro lo sustituye', async () => {
    const formulario = montar('', { subestado: 'Bloqueado' })
    expect(formulario.findAll('[data-testid="chip"]').map((chip) => chip.text())).toEqual([
      'Bloqueado',
    ])

    await escribirSubestado(formulario, 'en pausa')
    await formulario.get('input#subestado').trigger('keydown', { key: 'Enter' })
    await flushPromises()

    expect(valores().subestado).toBe('En pausa')
  })

  it('se puede crear un subestado nuevo y quitarlo', async () => {
    const formulario = montar()

    await escribirSubestado(formulario, 'Esperando cliente')
    await formulario.get('input#subestado').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(valores().subestado).toBe('Esperando cliente')

    await formulario.get('button[aria-label="Quitar Esperando cliente"]').trigger('click')
    await flushPromises()
    expect(valores().subestado).toBe('')
  })
})
