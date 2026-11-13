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
})
