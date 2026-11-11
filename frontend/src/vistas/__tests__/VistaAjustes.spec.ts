import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import router from '@/router'
import VistaAjustes from '../VistaAjustes.vue'
import VistaGruposEstados from '../VistaGruposEstados.vue'
import VistaWorkflowOportunidades from '../VistaWorkflowOportunidades.vue'

function crearRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/ajustes', component: VistaAjustes },
      { path: '/ajustes/workflow-oportunidades', component: { template: '<div />' } },
      { path: '/ajustes/grupos-estados', component: { template: '<div />' } },
    ],
  })
}

describe('VistaAjustes', () => {
  it('muestra la opción "Workflow Oportunidades" enlazada a su página', async () => {
    const enrutador = crearRouter()
    await enrutador.push('/ajustes')
    const contenedor = mount(VistaAjustes, { global: { plugins: [enrutador] } })

    const enlace = contenedor.get('a[href="/ajustes/workflow-oportunidades"]')
    expect(enlace.text()).toContain('Workflow Oportunidades')
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
  it('la ruta /ajustes/workflow-oportunidades muestra VistaWorkflowOportunidades', () => {
    const resuelta = router.resolve('/ajustes/workflow-oportunidades')

    expect(resuelta.name).toBe('workflow-oportunidades')
    expect(resuelta.matched[0]?.components?.default).toBe(VistaWorkflowOportunidades)
  })

  it('la ruta /ajustes/grupos-estados muestra VistaGruposEstados', () => {
    const resuelta = router.resolve('/ajustes/grupos-estados')

    expect(resuelta.name).toBe('grupos-estados')
    expect(resuelta.matched[0]?.components?.default).toBe(VistaGruposEstados)
  })
})
