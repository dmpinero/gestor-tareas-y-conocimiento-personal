import { test as base, expect } from '@playwright/test'

// La app lee la versión y el historial de cambios de la API pública de GitHub,
// que admite 60 peticiones por hora por IP sin token: si los e2e la llamaran de
// verdad agotarían el cupo de quien los ejecuta (y la versión desaparecería de
// la app). Todos los tests usan este `test`, que simula esa API en el contexto;
// un test puede sustituirla con `page.route`, que tiene prioridad.
export const VERSION_SIMULADA = 'v0.0.0-e2e'

export const test = base.extend<{ githubSimulado: void }>({
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
