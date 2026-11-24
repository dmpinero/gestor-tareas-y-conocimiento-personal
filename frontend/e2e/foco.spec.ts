import { test, expect, NOMBRE_GRUPO_E2E } from './base'

// La tarea en foco es única y vive en el servidor: el test deja el foco
// quitado al terminar para no afectar a los demás.
test.afterEach(async ({ request }) => {
  await request.delete('/api/v1/foco')
})

test('pone en foco una tarea y luego una subtarea desde el tablero y la píldora lo refleja', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = `Foco${Date.now()}`
  const nombreTarea = `${marca} tarea`
  const nombreSubtarea = `${marca} subtarea`
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre: nombreTarea,
      descripcion: 'Foco',
      fecha_creacion: '2026-01-01T09:00:00',
      grupo_estados_id: grupoE2e,
    },
  })
  expect(creada.status()).toBe(201)
  const { id } = (await creada.json()) as { id: number }
  const conSubtarea = await request.post(`/api/v1/tareas/${id}/subtareas`, {
    data: { nombre: nombreSubtarea },
  })
  expect(conSubtarea.ok()).toBe(true)
  await request.delete('/api/v1/foco')

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({
    label: NOMBRE_GRUPO_E2E,
  })
  await page.getByLabel('Buscar').fill(marca)
  const pildora = page.locator('[data-indicador-foco]')
  await expect(pildora).toBeHidden()

  // Tarea en foco: la tarjeta se marca y la píldora la nombra.
  const tarjeta = page.locator('[data-tarjeta]', { hasText: nombreTarea })
  await tarjeta.getByRole('button', { name: `Trabajar en esta (${nombreTarea})` }).click()
  await expect(pildora).toContainText(`Trabajando en: ${nombreTarea}`)
  await expect(pildora).toContainText('< 1 min')
  await expect(tarjeta).toHaveAttribute('data-en-foco', 'true')
  await expect(tarjeta.getByText('En foco')).toBeVisible()

  // Subtarea en foco: sustituye a la tarea y solo ella queda marcada.
  await tarjeta.getByRole('button', { name: `1 subtareas de ${nombreTarea}` }).click()
  const subtarea = page.locator('[data-subtarea]', { hasText: nombreSubtarea })
  await subtarea.getByRole('button', { name: `Trabajar en esta (${nombreSubtarea})` }).click()
  await expect(pildora).toContainText(`Trabajando en: ${nombreTarea} › ${nombreSubtarea}`)
  await expect(subtarea).toHaveAttribute('data-en-foco', 'true')
  await expect(tarjeta).not.toHaveAttribute('data-en-foco', 'true')
  await expect(
    page.locator('[data-tarjeta][data-en-foco="true"], [data-subtarea][data-en-foco="true"]'),
  ).toHaveCount(1)
  await page.screenshot({ path: 'e2e/capturas/foco-01-subtarea.png' })

  // Pulsar la píldora abre el detalle de la tarea.
  await pildora.locator('[data-abrir-foco]').click()
  await expect(page.getByRole('dialog', { name: nombreTarea })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog', { name: nombreTarea })).toBeHidden()

  // El ✕ deja de trabajar: la píldora desaparece.
  await pildora.getByRole('button', { name: 'Dejar de trabajar' }).click()
  await expect(pildora).toBeHidden()
  await expect(page.locator('[data-subtarea][data-en-foco="true"]')).toHaveCount(0)
})

test('en un móvil la barra superior no desborda la página, con foco o sin él', async ({
  page,
  request,
  grupoE2e,
}) => {
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre: `Foco${Date.now()} con un nombre bastante largo para la píldora de la barra`,
      descripcion: 'Foco',
      fecha_creacion: '2026-01-01T09:00:00',
      grupo_estados_id: grupoE2e,
    },
  })
  const { id } = (await creada.json()) as { id: number }
  await page.setViewportSize({ width: 390, height: 844 })
  const desborda = () =>
    page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)

  await request.delete('/api/v1/foco')
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Historial de foco' })).toBeVisible()
  expect(await desborda()).toBe(false)

  await request.put('/api/v1/foco', { data: { tarea_id: id } })
  await page.reload()
  await expect(page.locator('[data-indicador-foco]')).toBeVisible()
  expect(await desborda()).toBe(false)
})
