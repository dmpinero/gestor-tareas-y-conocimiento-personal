import AxeBuilder from '@axe-core/playwright'
import { test, expect, type Page } from './base'
import { activarModoOscuro } from './utilidades'

async function sinViolaciones(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
}

// El backend de e2e no tiene credenciales: Conocimiento lo explica y no deja
// sincronizar ni preguntar.
test('sin credenciales, Conocimiento explica qué falta configurar', async ({ page }) => {
  await page.goto('/conocimiento')
  await expect(page.getByTestId('falta-notion')).toContainText(
    'Falta configurar NOTION_TOKEN en backend/.env',
  )
  await expect(page.getByTestId('falta-anthropic')).toContainText(
    'Falta configurar ANTHROPIC_API_KEY en backend/.env',
  )
  await expect(page.getByTestId('boton-sincronizar')).toBeDisabled()
  await expect(page.getByLabel('Pregunta')).toBeDisabled()
  await expect(page.getByTestId('boton-enviar')).toBeDisabled()
  await sinViolaciones(page)
})

// Con la API simulada en el navegador: estado configurado y una respuesta en
// streaming (SSE) con sus fuentes.
async function simularApi(page: Page): Promise<void> {
  await page.route('**/api/v1/conocimiento/estado', (ruta) =>
    ruta.fulfill({
      json: {
        configurado: { notion: true, anthropic: true },
        paginas: 3,
        fragmentos: 12,
        ultima_sincronizacion: '2026-11-26T10:00:00Z',
      },
    }),
  )
  await page.route('**/api/v1/conocimiento/preguntar', (ruta) =>
    ruta.fulfill({
      status: 200,
      headers: { 'content-type': 'text/event-stream' },
      body: [
        'event: fuentes',
        'data: [{"pagina_id":"p1","titulo":"Guía de despliegue","url":"https://www.notion.so/p1"}]',
        '',
        'event: texto',
        'data: {"delta":"Para desplegar, ejecuta "}',
        '',
        'event: texto',
        'data: {"delta":"**make deploy** [Guía de despliegue]."}',
        '',
        'event: fin',
        'data: {}',
        '',
        '',
      ].join('\n'),
    }),
  )
}

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`el chat muestra la respuesta con sus fuentes y es accesible (modo ${modo})`, async ({
    page,
  }) => {
    await simularApi(page)
    await page.goto('/conocimiento')
    await preparar(page)
    await page.goto('/conocimiento')
    await expect(page.getByTestId('estado-conocimiento')).toContainText('3')
    await expect(page.getByText('Pregunta lo que quieras sobre tus notas de Notion.')).toBeVisible()

    await page.getByLabel('Pregunta').fill('¿Cómo despliego?')
    await page.getByLabel('Pregunta').press('Enter')
    const respuesta = page.locator('[data-rol="asistente"]').last()
    await expect(respuesta).toContainText('Para desplegar, ejecuta make deploy')
    await expect(respuesta.locator('strong')).toHaveText('make deploy')
    const fuente = respuesta.getByRole('link', { name: 'Guía de despliegue' })
    await expect(fuente).toHaveAttribute('href', 'https://www.notion.so/p1')
    await expect(fuente).toHaveAttribute('target', '_blank')
    await expect(page.locator('[data-rol="usuario"]').last()).toContainText('¿Cómo despliego?')
    await page.screenshot({ path: `e2e/capturas/conocimiento-01-chat-${modo}.png` })
    await sinViolaciones(page)

    // «Nueva conversación» vacía el chat.
    await page.getByTestId('nueva-conversacion').click()
    await expect(page.locator('[data-rol]')).toHaveCount(0)

    await page.setViewportSize({ width: 390, height: 844 })
    const ancho = await page.evaluate(() => document.documentElement.scrollWidth)
    expect(ancho).toBeLessThanOrEqual(390)
  })
}
