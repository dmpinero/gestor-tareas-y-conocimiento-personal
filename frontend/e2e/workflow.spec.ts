import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

// Cada test crea sus propios workflows con nombres únicos: no comparten estado.

function pasosDe(page: Page, workflow: string) {
  return page.getByRole('list', { name: `Pasos de ${workflow}` }).locator('[data-texto-paso]')
}

async function crearWorkflow(page: Page, workflow: string, pasos: string[]): Promise<void> {
  await page.goto('/ajustes')
  await page.getByRole('link', { name: 'Workflows' }).click()
  await expect(page).toHaveURL(/\/ajustes\/workflows$/)
  await page.getByLabel('Nombre del workflow').fill(workflow)
  await page.getByRole('button', { name: 'Añadir workflow' }).click()
  await expect(page.getByRole('heading', { name: workflow })).toBeVisible()
  for (const paso of pasos) {
    await page.getByRole('textbox', { name: `Nuevo paso de ${workflow}` }).fill(paso)
    await page.getByRole('button', { name: `Añadir paso a ${workflow}` }).click()
    await expect(pasosDe(page, workflow).filter({ hasText: paso })).toHaveCount(1)
  }
}

async function sinViolaciones(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
}

test('la ruta antigua del workflow lleva a la página de workflows', async ({ page }) => {
  await page.goto('/ajustes/workflow-oportunidades')
  await expect(page).toHaveURL(/\/ajustes\/workflows$/)
  await expect(page.getByRole('heading', { name: 'Workflows', exact: true })).toBeVisible()
})

test('gestiona varios workflows y sus pasos desde Ajustes', async ({ page }) => {
  const marca = Date.now()
  const workflow = `Ventas ${marca}`
  await crearWorkflow(page, workflow, ['Contactar', 'Proponer', 'Cerrar'])
  await expect(pasosDe(page, workflow)).toHaveText(['1. Contactar', '2. Proponer', '3. Cerrar'])

  // Obligatorio.
  await page.getByRole('button', { name: `Añadir paso a ${workflow}` }).click()
  await expect(page.getByText('El nombre del paso es obligatorio.')).toBeVisible()

  // Reordenar con los botones accesibles y con drag & drop.
  await page.getByRole('button', { name: `Bajar paso Contactar de ${workflow}` }).click()
  await expect(pasosDe(page, workflow)).toHaveText(['1. Proponer', '2. Contactar', '3. Cerrar'])
  await expect(page.locator('[aria-live="polite"]')).toContainText(
    'Contactar movido a la posición 2',
  )
  const filas = page.getByRole('list', { name: `Pasos de ${workflow}` }).locator('li[data-paso]')
  await filas.filter({ hasText: 'Cerrar' }).dragTo(filas.filter({ hasText: 'Proponer' }))
  await expect(pasosDe(page, workflow)).toHaveText(['1. Cerrar', '2. Proponer', '3. Contactar'])
  await page.screenshot({ path: 'e2e/capturas/workflow-01-pasos.png' })

  // Renombrar y eliminar un paso (los siguientes se renumeran).
  await page.getByRole('button', { name: `Renombrar paso Proponer de ${workflow}` }).click()
  await page.getByLabel(`Nuevo nombre del paso Proponer de ${workflow}`).fill('Enviar propuesta')
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.getByRole('button', { name: `Eliminar paso Cerrar de ${workflow}` }).click()
  await page
    .getByRole('alertdialog', { name: '¿Eliminar el paso Cerrar?' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(pasosDe(page, workflow)).toHaveText(['1. Enviar propuesta', '2. Contactar'])

  // Renombrar el workflow; se guarda al recargar.
  await page.getByRole('button', { name: `Renombrar workflow ${workflow}` }).click()
  await page.getByLabel(`Nuevo nombre del workflow ${workflow}`).fill(`${workflow} B2B`)
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.reload()
  await expect(pasosDe(page, `${workflow} B2B`)).toHaveText(['1. Enviar propuesta', '2. Contactar'])
  await sinViolaciones(page)

  // Eliminar el workflow avisa de que las tareas conservan sus subtareas.
  await page.getByRole('button', { name: `Eliminar workflow ${workflow} B2B` }).click()
  const confirmar = page.getByRole('alertdialog', {
    name: `¿Eliminar el workflow ${workflow} B2B?`,
  })
  await expect(confirmar).toContainText('conservarán sus subtareas')
  await confirmar.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByRole('heading', { name: `${workflow} B2B` })).toHaveCount(0)
})

test('el workflow de la tarea añade sus pasos como subtareas al crearla y al cambiarlo', async ({
  page,
}) => {
  const marca = Date.now()
  const primero = `Alta ${marca}`
  const segundo = `Cierre ${marca}`
  const tarea = `Tarea con workflow ${marca}`
  await crearWorkflow(page, primero, ['Llamar', 'Visitar'])
  await crearWorkflow(page, segundo, ['Facturar'])

  // Alta con el primer workflow: sus pasos llegan como subtareas.
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  await ventana.getByPlaceholder('Nombre').fill(tarea)
  await ventana.getByPlaceholder('Descripción').fill('Con workflow')
  await ventana.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: primero })
  await ventana.getByRole('button', { name: 'Guardar' }).click()
  await expect(ventana).toBeHidden()

  const abrirDetalle = async () => {
    await page.getByRole('button', { name: `Ver detalle de la tarea ${tarea}` }).click()
    return page.getByRole('dialog', { name: tarea })
  }
  let detalle = await abrirDetalle()
  await expect(detalle.getByTestId('campos-tarea')).toContainText(primero)
  for (const paso of ['Llamar', 'Visitar']) {
    await expect(
      detalle.getByRole('button', { name: `Marcar como resuelta la subtarea ${paso}` }),
    ).toBeVisible()
  }
  await page.keyboard.press('Escape')

  // Editar y elegir otro workflow: añade sus pasos y conserva los anteriores.
  await page.getByRole('button', { name: `Editar tarea ${tarea}` }).click()
  const edicion = page.getByRole('dialog', { name: 'Editar tarea' })
  await expect(edicion.getByRole('combobox', { name: 'Workflow' })).toHaveValue(/\d+/)
  await edicion.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: segundo })
  await edicion.getByRole('button', { name: 'Guardar' }).click()
  await expect(edicion).toBeHidden()

  detalle = await abrirDetalle()
  for (const paso of ['Llamar', 'Visitar', 'Facturar']) {
    await expect(
      detalle.getByRole('button', { name: `Marcar como resuelta la subtarea ${paso}` }),
    ).toBeVisible()
  }
  await page.screenshot({ path: 'e2e/capturas/workflow-02-pasos-tarea.png' })
})

test('al elegir el tipo Oportunidad en el alta se preselecciona "Workflow Oportunidades"', async ({
  page,
}) => {
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  const workflow = ventana.getByRole('combobox', { name: 'Workflow' })
  await expect(workflow).toHaveValue('')
  await ventana.getByLabel('Tipo de tarea').selectOption({ label: 'Oportunidad' })
  await expect(workflow.locator('option:checked')).toHaveText('Workflow Oportunidades')
})

// Regresión (accesibilidad): al mover con el teclado, el foco se perdía en el
// <body> porque el botón pulsado se desactiva mientras se guarda.
test('al reordenar con el teclado el foco se queda en el paso movido', async ({ page }) => {
  const workflow = `Teclado ${Date.now()}`
  await crearWorkflow(page, workflow, ['Uno', 'Dos', 'Tres'])

  await page.getByRole('button', { name: `Bajar paso Uno de ${workflow}` }).focus()
  await page.keyboard.press('Enter')
  await expect(pasosDe(page, workflow)).toHaveText(['1. Dos', '2. Uno', '3. Tres'])
  await expect(page.getByRole('button', { name: `Bajar paso Uno de ${workflow}` })).toBeFocused()

  await page.keyboard.press('Enter')
  await expect(pasosDe(page, workflow)).toHaveText(['1. Dos', '2. Tres', '3. Uno'])
  // Ya está al final: el foco pasa a su botón "Subir".
  await expect(page.getByRole('button', { name: `Subir paso Uno de ${workflow}` })).toBeFocused()
})
