import { test as base, expect } from '@playwright/test'

// La app lee la versión y el historial de cambios de la API pública de GitHub,
// que admite 60 peticiones por hora por IP sin token: si los e2e la llamaran de
// verdad agotarían el cupo de quien los ejecuta (y la versión desaparecería de
// la app). Todos los tests usan este `test`, que simula esa API en el contexto;
// un test puede sustituirla con `page.route`, que tiene prioridad.
export const VERSION_SIMULADA = 'v0.0.0-e2e'

// El grupo de estados es obligatorio al crear y editar tareas desde la app: cada
// test parte de que existe al menos uno con estados (lo crea si no hay), que
// el formulario propone. `grupoE2e` es su id, para crear tareas por la API.
export const NOMBRE_GRUPO_E2E = 'Grupo e2e'

export const test = base.extend<{ githubSimulado: void; grupoE2e: number }>({
  grupoE2e: [
    async ({ request }, usar) => {
      const respuesta = await request.get('/api/v1/grupos-estados')
      expect(respuesta.ok()).toBe(true)
      const grupos = (await respuesta.json()) as {
        id: number
        nombre: string
        estados: unknown[]
      }[]
      let grupo = grupos.find((g) => g.nombre === NOMBRE_GRUPO_E2E)
      if (grupo === undefined) {
        const creado = await request.post('/api/v1/grupos-estados', {
          data: { nombre: NOMBRE_GRUPO_E2E },
        })
        expect(creado.status()).toBe(201)
        grupo = {
          ...((await creado.json()) as { id: number }),
          nombre: NOMBRE_GRUPO_E2E,
          estados: [],
        }
      }
      const id = grupo.id
      if (grupo.estados.length === 0) {
        const estado = await request.post(`/api/v1/grupos-estados/${id}/estados`, {
          data: { nombre: 'Por hacer' },
        })
        expect(estado.status()).toBe(201)
      }
      await usar(id)
    },
    { auto: true },
  ],
  githubSimulado: [
    async ({ context }, usar) => {
      await context.route('https://api.github.com/**', async (ruta) => {
        const url = ruta.request().url()
        if (url.includes('/releases/latest')) {
          await ruta.fulfill({ json: { tag_name: VERSION_SIMULADA, name: VERSION_SIMULADA } })
        } else if (url.includes('/releases')) {
          await ruta.fulfill({ json: [] })
        } else {
          await ruta.fulfill({ status: 404, json: { message: 'Not Found' } })
        }
      })
      await usar()
    },
    { auto: true },
  ],
})

export { expect }
export type { APIRequestContext, Locator, Page } from '@playwright/test'
