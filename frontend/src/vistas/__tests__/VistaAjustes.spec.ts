import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import router from '@/router'
import VistaAjustes from '../VistaAjustes.vue'
import VistaGruposEstados from '../VistaGruposEstados.vue'
import VistaWorkflows from '../VistaWorkflows.vue'

function crearRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: VistaAjustes },
      { path: '/ajustes/workflows', component: { template: '<div />' } },
      { path: '/ajustes/grupos-estados', component: { template: '<div />' } },
    ],
  })
}

describe('VistaAjustes', () => {
  it('muestra la opción "Workflows" enlazada a su página', async () => {
    const enrutador = crearRouter()
    await enrutador.push('/ajustes')
    const contenedor = mount(VistaAjustes, { global: { plugins: [enrutador] } })

    const enlace = contenedor.get('a[href="/ajustes/workflows"]')
    expect(enlace.get('.font-medium').text()).toBe('Workflows')
    expect(contenedor.find('a[href="/ajustes/workflow-oportunidades"]').exists()).toBe(false)
    expect(contenedor.text()).not.toContain('Todavía no hay ajustes configurables.')
  })

  it('muestra la opción "Grupos de estados" enlazada a su página', async () => {
    const enrutador = crearRouter()
    await enrutador.push('/ajustes')
    const contenedor = mount(VistaAjustes, { global: { plugins: [enrutador] } })

    const enlace = contenedor.get('a[href="/ajustes/grupos-estados"]')
    expect(enlace.text()).toContain('Grupos de estados')
  })
})

describe('router', () => {
  it('la ruta /ajustes/workflows muestra VistaWorkflows', () => {
    const resuelta = router.resolve('/ajustes/workflows')

    expect(resuelta.name).toBe('workflows')
    expect(resuelta.matched[0]?.components?.default).toBe(VistaWorkflows)
  })

  it('la ruta antigua /ajustes/workflow-oportunidades redirige a /ajustes/workflows', async () => {
    await router.push('/ajustes/workflow-oportunidades')

    expect(router.currentRoute.value.path).toBe('/ajustes/workflows')
    expect(router.currentRoute.value.name).toBe('workflows')
  })

  it('la ruta /ajustes/grupos-estados muestra VistaGruposEstados', () => {
    const resuelta = router.resolve('/ajustes/grupos-estados')

    expect(resuelta.name).toBe('grupos-estados')
    expect(resuelta.matched[0]?.components?.default).toBe(VistaGruposEstados)
  })
})
