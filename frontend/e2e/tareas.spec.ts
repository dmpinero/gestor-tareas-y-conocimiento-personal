import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('crea una tarea desde el panel lateral y aparece en el listado', async ({ page }) => {
  // Nombre único: la base de datos de la pila local no se vacía entre ejecuciones.
  const nombre = `Tarea e2e ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()

  const panel = page.getByRole('dialog')
  await expect(panel).toBeVisible()
  await expect(panel.getByRole('heading', { name: 'Crear tarea' })).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/tareas-01-panel-crear.png' })

  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Prioridad').fill('2')
  await panel.getByPlaceholder('Descripción').fill('Descripción creada desde el test e2e')
  await panel.getByRole('button', { name: 'Guardar' }).click()

  await expect(panel).toBeHidden()
  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toBeVisible()
  await expect(fila).toContainText('2')
  await expect(fila).toContainText('Descripción creada desde el test e2e')
  await page.screenshot({ path: 'e2e/capturas/tareas-02-listado.png' })
})

test('una tarea sin prioridad se muestra con un guion', async ({ page }) => {
  const nombre = `Tarea sin prioridad ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()

  const panel = page.getByRole('dialog')
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Sin prioridad')
  await panel.getByRole('button', { name: 'Guardar' }).click()

  await expect(panel).toBeHidden()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('—')
})

test('el listado sigue siendo accesible con nombres y descripciones de longitud máxima', async ({
  page,
}) => {
  // Regresión: con `whitespace-nowrap` un nombre largo desbordaba la tabla en
  // horizontal y axe marcaba `scrollable-region-focusable`.
  const marca = `${Date.now()}`
  const conEspacios = `${marca} ${'palabra '.repeat(30)}`.slice(0, 200)
  const sinEspacios = `${marca}${'x'.repeat(200)}`.slice(0, 200)

  await page.goto('/tareas')
  for (const nombre of [conEspacios, sinEspacios]) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByPlaceholder('Nombre').fill(nombre)
    await panel.getByPlaceholder('Descripción').fill('d'.repeat(500))
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
})
