import { test, expect, type APIRequestContext, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// El workflow es global: estos tests cambian su estado y se ejecutan en serie,
// partiendo siempre de un workflow vacío.
test.describe.configure({ mode: 'serial' })

const API_PASOS = '/api/v1/workflow-oportunidades/pasos'

async function vaciarWorkflow(request: APIRequestContext) {
  const respuesta = await request.get(API_PASOS)
  expect(respuesta.ok()).toBe(true)
  for (const paso of (await respuesta.json()) as { id: number }[]) {
    expect((await request.delete(`${API_PASOS}/${paso.id}`)).status()).toBe(204)
  }
}

function textosDePasos(page: Page) {
  return page.getByRole('list', { name: 'Pasos del workflow' }).locator('[data-texto-paso]')
}

async function anadirPaso(page: Page, nombre: string) {
  await page.getByLabel('Nombre del paso').fill(nombre)
  await page.getByRole('button', { name: 'Añadir paso' }).click()
  await expect(textosDePasos(page).filter({ hasText: nombre })).toHaveCount(1)
}

test.beforeEach(async ({ request }) => {
  await vaciarWorkflow(request)
})

test.afterAll(async ({ request }) => {
  await vaciarWorkflow(request)
})

test('gestiona los pasos del workflow desde Ajustes y los reordena', async ({ page }) => {
  await page.goto('/ajustes')
  await page.getByRole('link', { name: 'Workflow Oportunidades' }).click()
  await expect(page).toHaveURL(/\/ajustes\/workflow-oportunidades$/)
  await expect(page.getByRole('heading', { name: 'Workflow Oportunidades' })).toBeVisible()
  await expect(page.getByText('Todavía no hay pasos en el workflow.')).toBeVisible()

  // Cada paso nuevo es continuación del anterior.
  for (const nombre of ['Contactar', 'Proponer', 'Cerrar']) await anadirPaso(page, nombre)
  await expect(textosDePasos(page)).toHaveText(['1. Contactar', '2. Proponer', '3. Cerrar'])

  // Obligatorio y máximo 50 caracteres.
  await page.getByRole('button', { name: 'Añadir paso' }).click()
  await expect(page.getByText('El nombre del paso es obligatorio.')).toBeVisible()

  // Reordenar con los botones accesibles.
  await page.getByRole('button', { name: 'Bajar paso Contactar' }).click()
  await expect(textosDePasos(page)).toHaveText(['1. Proponer', '2. Contactar', '3. Cerrar'])
  await expect(page.locator('[aria-live="polite"]')).toContainText(
    'Contactar movido a la posición 2',
  )
  await expect(page.getByRole('button', { name: 'Subir paso Proponer' })).toBeDisabled()

  // Reordenar con drag & drop: "Cerrar" sobre el primer paso.
  const filas = page.getByRole('list', { name: 'Pasos del workflow' }).locator('li[data-paso]')
  await filas.filter({ hasText: 'Cerrar' }).dragTo(filas.filter({ hasText: 'Proponer' }))
  await expect(textosDePasos(page)).toHaveText(['1. Cerrar', '2. Proponer', '3. Contactar'])
  await page.screenshot({ path: 'e2e/capturas/workflow-01-pasos.png' })

  // Renombrar y eliminar (los siguientes se renumeran).
  await page.getByRole('button', { name: 'Renombrar paso Proponer' }).click()
  await page.getByLabel('Nuevo nombre del paso Proponer').fill('Enviar propuesta')
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.getByRole('button', { name: 'Eliminar paso Cerrar' }).click()
  await page
    .getByRole('dialog', { name: 'Eliminar paso' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(textosDePasos(page)).toHaveText(['1. Enviar propuesta', '2. Contactar'])

  // Se guarda: sigue igual al recargar.
  await page.reload()
  await expect(textosDePasos(page)).toHaveText(['1. Enviar propuesta', '2. Contactar'])

  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
})

test('una oportunidad nueva recibe los pasos del workflow como subtareas y se marca su avance', async ({
  page,
}) => {
  const nombre = `Oportunidad con pasos ${Date.now()}`

  await page.goto('/ajustes/workflow-oportunidades')
  for (const paso of ['Llamar', 'Visitar', 'Firmar']) await anadirPaso(page, paso)

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog', { name: 'Crear tarea' })
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Con los pasos del workflow')
  await panel.getByLabel('Tipo de tarea').selectOption({ label: 'Oportunidad' })
  await panel.getByLabel('Código de la oportunidad').fill('OP-PASOS')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toContainText('Oportunidad · 0/3')

  await fila.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  // Los pasos llegan como subtareas, en orden y sin resolver.
  await expect(detalle.getByTestId('pasos-oportunidad')).toHaveCount(0)
  for (const paso of ['Llamar', 'Visitar', 'Firmar']) {
    await expect(
      detalle.getByRole('button', { name: `Marcar como resuelta la subtarea ${paso}` }),
    ).toHaveAttribute('aria-pressed', 'false')
  }
  await detalle.getByRole('button', { name: 'Marcar como resuelta la subtarea Llamar' }).click()
  await expect(
    detalle.getByRole('button', { name: 'Marcar como resuelta la subtarea Llamar' }),
  ).toHaveAttribute('aria-pressed', 'true')
  await page.screenshot({ path: 'e2e/capturas/workflow-02-pasos-tarea.png' })
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()
  await expect(fila).toContainText('Oportunidad · 1/3')

  // Copia fija: cambiar el workflow no altera la tarea ya creada.
  await page.goto('/ajustes/workflow-oportunidades')
  await anadirPaso(page, 'Facturar')
  await page.goto('/tareas')
  await expect(page.locator('tr', { hasText: nombre })).toContainText('Oportunidad · 1/3')
})

// Regresión (accesibilidad): al mover con el teclado, el foco se perdía en el
// <body> porque el botón pulsado se desactiva mientras se guarda.
test('al reordenar con el teclado el foco se queda en el paso movido', async ({ page }) => {
  await page.goto('/ajustes/workflow-oportunidades')
  for (const nombre of ['Uno', 'Dos', 'Tres']) await anadirPaso(page, nombre)

  await page.getByRole('button', { name: 'Bajar paso Uno' }).focus()
  await page.keyboard.press('Enter')
  await expect(textosDePasos(page)).toHaveText(['1. Dos', '2. Uno', '3. Tres'])
  await expect(page.getByRole('button', { name: 'Bajar paso Uno' })).toBeFocused()

  await page.keyboard.press('Enter')
  await expect(textosDePasos(page)).toHaveText(['1. Dos', '2. Tres', '3. Uno'])
  // Ya está al final: el foco pasa a su botón "Subir".
  await expect(page.getByRole('button', { name: 'Subir paso Uno' })).toBeFocused()

  await page.getByRole('button', { name: 'Eliminar paso Uno' }).click()
  await page
    .getByRole('dialog', { name: 'Eliminar paso' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(page.getByLabel('Nombre del paso')).toBeFocused()
})
