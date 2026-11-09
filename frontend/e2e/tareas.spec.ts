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

test('la fecha y hora se rellena con la actual y se puede editar una tarea', async ({ page }) => {
  const nombre = `Tarea a editar ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog')
  await expect(panel.getByPlaceholder('dd/mm/aaaa hh:mm:ss')).toHaveValue(
    /^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}$/,
  )
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Antes de editar')
  await panel.getByPlaceholder('dd/mm/aaaa hh:mm:ss').fill('09/11/2026 08:30:15')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('09/11/2026 08:30:15')

  await page.getByRole('button', { name: `Editar tarea ${nombre}` }).click()
  await expect(panel.getByRole('heading', { name: 'Editar tarea' })).toBeVisible()
  await expect(panel.getByPlaceholder('Nombre')).toHaveValue(nombre)
  await expect(panel.getByPlaceholder('dd/mm/aaaa hh:mm:ss')).toHaveValue('09/11/2026 08:30:15')
  await page.screenshot({ path: 'e2e/capturas/tareas-03-panel-editar.png' })

  await panel.getByPlaceholder('Descripción').fill('Después de editar')
  await panel.getByPlaceholder('Prioridad').fill('1')
  await panel.getByPlaceholder('dd/mm/aaaa hh:mm:ss').fill('31/12/2026 23:59:59')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toContainText('Después de editar')
  await expect(fila).toContainText('31/12/2026 23:59:59')
  await page.reload()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('Después de editar')
})

test('ordena la tabla por una columna y exporta el listado a Excel y PDF', async ({ page }) => {
  const marca = `${Date.now()}`
  const nombres = [`zz ${marca}`, `aa ${marca}`]

  await page.goto('/tareas')
  for (const nombre of nombres) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByPlaceholder('Nombre').fill(nombre)
    await panel.getByPlaceholder('Descripción').fill('Para ordenar y exportar')
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const cabeceraNombre = page.getByRole('columnheader', { name: 'Nombre' })
  const filasDeLaPrueba = page.locator('tbody tr', { hasText: marca })

  await cabeceraNombre.getByRole('button', { name: 'Nombre' }).click()
  await expect(cabeceraNombre).toHaveAttribute('aria-sort', 'ascending')
  await expect(filasDeLaPrueba.first()).toContainText(`aa ${marca}`)

  await cabeceraNombre.getByRole('button', { name: 'Nombre' }).click()
  await expect(cabeceraNombre).toHaveAttribute('aria-sort', 'descending')
  await expect(filasDeLaPrueba.first()).toContainText(`zz ${marca}`)
  await page.screenshot({ path: 'e2e/capturas/tareas-04-ordenada.png' })

  const [descargaExcel] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Exportar a Excel' }).click(),
  ])
  expect(descargaExcel.suggestedFilename()).toMatch(/^Tareas_\d{8}_\d{6}\.xlsx$/)

  const [descargaPdf] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Exportar a PDF' }).click(),
  ])
  expect(descargaPdf.suggestedFilename()).toMatch(/^Tareas_\d{8}_\d{6}\.pdf$/)
})
