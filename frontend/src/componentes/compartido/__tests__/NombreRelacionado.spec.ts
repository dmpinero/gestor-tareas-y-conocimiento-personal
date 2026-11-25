import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { useProveedorTareasRelacionadas } from '@/composables/useTareasRelacionadas'
import NombreRelacionado from '../NombreRelacionado.vue'

describe('NombreRelacionado', () => {
  it('sin una vista que ofrezca el modal es solo texto', () => {
    const envoltorio = mount(NombreRelacionado, { props: { tipo: 'etiqueta', nombre: 'Urgente' } })
    expect(envoltorio.find('button').exists()).toBe(false)
    expect(envoltorio.text()).toBe('Urgente')
  })

  it('dentro de la vista es un botón que abre el modal con su tipo y nombre', async () => {
    let proveedor: ReturnType<typeof useProveedorTareasRelacionadas> | null = null
    const vista = defineComponent({
      setup() {
        proveedor = useProveedorTareasRelacionadas()
        return () => h(NombreRelacionado, { tipo: 'persona', nombre: 'Ana' })
      },
    })
    const envoltorio = mount(vista)
    const boton = envoltorio.get('button')
    expect(boton.text()).toBe('Ana')
    expect(boton.attributes('aria-label')).toBe('Ver tareas y subtareas de Ana')

    await boton.trigger('click')
    expect(proveedor!.seleccion.value).toEqual({ tipo: 'persona', nombre: 'Ana' })
  })

  it('un subestado abre el modal con su nombre y lo dice en su nombre accesible', async () => {
    let proveedor: ReturnType<typeof useProveedorTareasRelacionadas> | null = null
    const vista = defineComponent({
      setup() {
        proveedor = useProveedorTareasRelacionadas()
        return () => h(NombreRelacionado, { tipo: 'subestado', nombre: 'Bloqueada' })
      },
    })
    const boton = mount(vista).get('button')
    expect(boton.attributes('aria-label')).toBe('Ver tareas con el subestado Bloqueada')

    await boton.trigger('click')
    expect(proveedor!.seleccion.value).toEqual({ tipo: 'subestado', nombre: 'Bloqueada' })
  })

  it.each([
    ['prioridad', '2', 'Ver tareas y subtareas con la prioridad 2'],
    ['estado', 'En curso', 'Ver tareas en el estado En curso'],
    ['tipo', 'Oportunidad', 'Ver tareas de tipo Oportunidad'],
    ['completado', 'Completada', 'Ver tareas: Completada'],
    ['completado', 'Pendiente', 'Ver tareas: Pendiente'],
    ['hibernada', 'Hibernada', 'Ver tareas: Hibernada'],
  ] as const)(
    '%s %s abre el modal y lo dice en su nombre accesible',
    async (tipo, nombre, accesible) => {
      let proveedor: ReturnType<typeof useProveedorTareasRelacionadas> | null = null
      const vista = defineComponent({
        setup() {
          proveedor = useProveedorTareasRelacionadas()
          return () => h(NombreRelacionado, { tipo, nombre })
        },
      })
      const boton = mount(vista).get('button')
      expect(boton.attributes('aria-label')).toBe(accesible)

      await boton.trigger('click')
      expect(proveedor!.seleccion.value).toEqual({ tipo, nombre })
    },
  )

  it('admite otro contenido (p. ej. un avatar) sin cambiar su nombre accesible', () => {
    const vista = defineComponent({
      setup() {
        useProveedorTareasRelacionadas()
        return () =>
          h(NombreRelacionado, { tipo: 'persona', nombre: 'Ana' }, { default: () => 'AN' })
      },
    })
    const boton = mount(vista).get('button')
    expect(boton.text()).toBe('AN')
    expect(boton.attributes('aria-label')).toBe('Ver tareas y subtareas de Ana')
  })
})
