import { test, expect } from './base'

// El foco es único y vive en el servidor: se quita antes y después para no
// afectar a los demás tests. El historial es compartido, así que solo se miran
// las entradas con la marca de este test.
test.beforeEach(async ({ request }) => {
  await request.delete('/api/v1/foco')
})

test.afterEach(async ({ request }) => {
  await request.delete('/api/v1/foco')
})

test('el historial de foco lista los cambios por día y en total, y lleva a la tarea', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = `Historial${Date.now()}`
  const nombreA = `${marca} A`
  const nombreB = `${marca} B`
  const ids: number[] = []
  for (const nombre of [nombreA, nombreB]) {
    const creada = await request.post('/api/v1/tareas', {
      data: {
        nombre,
        descripcion: 'Historial de foco',
        fecha_creacion: '2026-01-01T09:00:00',
        grupo_estados_id: grupoE2e,
      },
    })
    expect(creada.status()).toBe(201)
    ids.push(((await creada.json()) as { id: number }).id)
  }
  const [idA, idB] = ids
  expect(
    (await request.put('/api/v1/foco', { data: { tarea_id: idA, subtarea_id: null } })).ok(),
  ).toBe(true)
  expect(
    (await request.put('/api/v1/foco', { data: { tarea_id: idB, subtarea_id: null } })).ok(),
  ).toBe(true)

  await page.goto('/')
  await page.getByRole('button', { name: 'Historial de foco' }).click()
  await expect(page).toHaveURL(/\/foco\/historial/)
  await expect(page.getByRole('heading', { name: 'Historial de foco' })).toBeVisible()

  // Por día (hoy): B, la actual, en curso y primero; A cerrada después.
  const entradas = page.locator('[data-entrada-historial]', { hasText: marca })
  await expect(entradas).toHaveCount(2)
  await expect(entradas.nth(0)).toContainText(nombreB)
  await expect(entradas.nth(0)).toContainText('en curso')
  await expect(entradas.nth(1)).toContainText(nombreA)
  await expect(entradas.nth(1)).not.toContainText('en curso')
  await expect(page.getByRole('button', { name: 'Día siguiente' })).toBeDisabled()
  await page.screenshot({ path: 'e2e/capturas/historial-foco-01-dia.png' })

  // Todo: la tabla completa, la más reciente primero.
  await page.getByRole('button', { name: 'Todo', exact: true }).click()
  await expect(page).toHaveURL(/vista=todo/)
  await expect(page.getByRole('columnheader', { name: 'Duración' })).toBeVisible()
  await expect(entradas).toHaveCount(2)
  await expect(entradas.nth(0)).toContainText(nombreB)
  await expect(entradas.nth(1)).toContainText(nombreA)
  await page.screenshot({ path: 'e2e/capturas/historial-foco-02-todo.png' })

  // Pulsar A abre su detalle.
  await entradas.nth(1).getByRole('link', { name: nombreA }).click()
  // El enlace va a /tareas?tarea=<id>, que abre el detalle y quita el
  // parámetro (sin esperar si las tareas ya estaban cargadas, p. ej. por Inicio).
  await expect(page.getByRole('dialog', { name: nombreA })).toBeVisible()
  await expect(page).toHaveURL(/\/tareas$/)
})
