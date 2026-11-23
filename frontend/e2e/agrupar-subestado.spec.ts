import { test, expect, type APIRequestContext, type Page } from './base'
import AxeBuilder from '@axe-core/playwright'

// Cada test crea sus tareas, subestados y grupo de estados con una marca única
// y filtra por ella con el buscador, así no depende de lo que dejen otros tests.

async function sinViolaciones(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
}

async function sinDesbordar(page: Page): Promise<void> {
  const desborda = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(desborda).toBe(false)
}

async function crearTarea(
  request: APIRequestContext,
  nombre: string,
  extra: Record<string, unknown> = {},
): Promise<void> {
  const respuesta = await request.post('/api/v1/tareas', {
    data: { nombre, descripcion: 'Agrupar', fecha_creacion: '2026-01-01T09:00:00', ...extra },
  })
  expect(respuesta.status()).toBe(201)
}

test('agrupa la lista por subestado en secciones plegables y lo recuerda', async ({
  page,
  request,
}) => {
  const marca = `Lista${Date.now()}`
  const revision = `Revisión ${marca}`
  await crearTarea(request, `${marca} uno`, { subestado: revision })
  await crearTarea(request, `${marca} dos`, { subestado: revision })
  await crearTarea(request, `${marca} tres`)

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como lista' }).click()
  await page.getByLabel('Buscar').fill(marca)
  const agrupar = page.getByRole('button', { name: 'Agrupar por subestado' })
  await expect(agrupar).toHaveAttribute('aria-pressed', 'false')
  await agrupar.click()
  await expect(agrupar).toHaveAttribute('aria-pressed', 'true')

  const seccionRevision = page.getByRole('button', { name: `${revision} · 2` })
  const seccionSin = page.getByRole('button', { name: 'Sin subestado · 1' })
  await expect(seccionRevision).toHaveAttribute('aria-expanded', 'true')
  await expect(seccionSin).toBeVisible()
  await expect(page.locator('tr[data-fila-tarea]', { hasText: `${marca} uno` })).toBeVisible()

  // Plegar oculta sus filas; el resto sigue a la vista.
  await seccionRevision.click()
  await expect(seccionRevision).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('tr[data-fila-tarea]', { hasText: `${marca} uno` })).toBeHidden()
  await expect(page.locator('tr[data-fila-tarea]', { hasText: `${marca} tres` })).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/agrupar-01-lista.png' })
  await sinViolaciones(page)

  // Se recuerda al recargar: sigue agrupado y la sección plegada.
  await page.reload()
  await page.getByLabel('Buscar').fill(marca)
  await expect(page.getByRole('button', { name: 'Agrupar por subestado' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await expect(page.getByRole('button', { name: `${revision} · 2` })).toHaveAttribute(
    'aria-expanded',
    'false',
  )

  await page.setViewportSize({ width: 390, height: 844 })
  await sinDesbordar(page)
})

test('agrupa las tarjetas del tablero por subestado y mover solo cambia el estado', async ({
  page,
  request,
}) => {
  const marca = `Tablero${Date.now()}`
  const grupo = `Grupo ${marca}`
  const bloqueado = `Bloqueado ${marca}`
  const creado = await request.post('/api/v1/grupos-estados', { data: { nombre: grupo } })
  expect(creado.status()).toBe(201)
  const { id } = (await creado.json()) as { id: number }
  for (const estado of ['Pendiente', 'En curso']) {
    const respuesta = await request.post(`/api/v1/grupos-estados/${id}/estados`, {
      data: { nombre: estado },
    })
    expect(respuesta.status()).toBe(201)
  }
  await crearTarea(request, `${marca} uno`, { grupo_estados_id: id, subestado: bloqueado })
  await crearTarea(request, `${marca} dos`, { grupo_estados_id: id })

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({ label: grupo })
  await page.getByLabel('Buscar').fill(marca)
  await page.getByRole('button', { name: 'Agrupar por subestado' }).click()

  const pendiente = page.getByRole('region', { name: 'Estado Pendiente' })
  await expect(pendiente.getByRole('button', { name: `${bloqueado} (1 tarea)` })).toBeVisible()
  await expect(pendiente.getByRole('button', { name: 'Sin subestado (1 tarea)' })).toBeVisible()
  await expect(
    pendiente.getByRole('list', { name: `Tareas en Pendiente: ${bloqueado}` }),
  ).toContainText(`${marca} uno`)
  await page.screenshot({ path: 'e2e/capturas/agrupar-02-tablero.png' })
  await sinViolaciones(page)

  // "Mover a…" cambia el estado y la tarjeta conserva su subestado.
  await pendiente.getByRole('button', { name: `Mover a… (${marca} uno)` }).click()
  await page.getByRole('button', { name: 'En curso', exact: true }).click()
  const enCurso = page.getByRole('region', { name: 'Estado En curso' })
  await expect(
    enCurso.getByRole('list', { name: `Tareas en En curso: ${bloqueado}` }),
  ).toContainText(`${marca} uno`)
  await expect(enCurso.getByRole('button', { name: `Mover a… (${marca} uno)` })).toBeFocused()

  await page.setViewportSize({ width: 390, height: 844 })
  await sinDesbordar(page)
})

test('pulsar un subestado muestra todas las tareas con ese subestado', async ({
  page,
  request,
}) => {
  const marca = `Pulsar${Date.now()}`
  const bloqueada = `Bloqueada ${marca}`
  await crearTarea(request, `${marca} uno`, { subestado: bloqueada })
  await crearTarea(request, `${marca} dos`, { subestado: bloqueada })
  await crearTarea(request, `${marca} tres`)

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como lista' }).click()
  await page.getByLabel('Buscar').fill(marca)
  await page
    .locator('tr[data-fila-tarea]', { hasText: `${marca} uno` })
    .getByRole('button', { name: `Ver tareas con el subestado ${bloqueada}` })
    .click()

  const modal = page.getByRole('dialog', { name: `Subestado: ${bloqueada}` })
  await expect(modal).toContainText('Tareas con este subestado.')
  const tareas = modal.getByRole('list', { name: 'Tareas' })
  await expect(tareas).toContainText(`${marca} uno`)
  await expect(tareas).toContainText(`${marca} dos`)
  await expect(tareas).not.toContainText(`${marca} tres`)
  await page.screenshot({ path: 'e2e/capturas/agrupar-03-subestado-relacionadas.png' })
  await sinViolaciones(page)
})

test('arrastrar una tarjeta a otro grupo de subestado le cambia el subestado', async ({
  page,
  request,
}) => {
  const marca = `Arrastre${Date.now()}`
  const grupo = `Grupo ${marca}`
  const bloqueado = `Bloqueado ${marca}`
  const creado = await request.post('/api/v1/grupos-estados', { data: { nombre: grupo } })
  expect(creado.status()).toBe(201)
  const { id } = (await creado.json()) as { id: number }
  for (const estado of ['Pendiente', 'En curso']) {
    const respuesta = await request.post(`/api/v1/grupos-estados/${id}/estados`, {
      data: { nombre: estado },
    })
    expect(respuesta.status()).toBe(201)
  }
  await crearTarea(request, `${marca} uno`, { grupo_estados_id: id, subestado: bloqueado })
  await crearTarea(request, `${marca} dos`, { grupo_estados_id: id })
  const tres = await request.post('/api/v1/tareas', {
    data: {
      nombre: `${marca} tres`,
      descripcion: 'Agrupar',
      fecha_creacion: '2026-01-01T09:00:00',
      grupo_estados_id: id,
    },
  })
  expect(tres.status()).toBe(201)
  const { id: idTres } = (await tres.json()) as { id: number }
  const grupoCreado = (await (await request.get('/api/v1/grupos-estados')).json()) as {
    id: number
    estados: { id: number; nombre: string }[]
  }[]
  const enCursoId = grupoCreado.find((g) => g.id === id)!.estados[1]!.id
  expect(
    (
      await request.patch(`/api/v1/tareas/${idTres}/estado`, { data: { estado_id: enCursoId } })
    ).status(),
  ).toBe(200)

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({ label: grupo })
  await page.getByLabel('Buscar').fill(marca)
  await page.getByRole('button', { name: 'Agrupar por subestado' }).click()
  const pendiente = page.getByRole('region', { name: 'Estado Pendiente' })
  const enCurso = page.getByRole('region', { name: 'Estado En curso' })

  // Dentro de la misma columna: de "Sin subestado" al grupo del subestado.
  await pendiente
    .getByRole('button', { name: `${marca} dos`, exact: true })
    .dragTo(pendiente.getByRole('button', { name: `${bloqueado} (1 tarea)` }))
  await expect(pendiente.getByRole('button', { name: `${bloqueado} (2 tareas)` })).toBeVisible()
  await expect(pendiente.getByRole('button', { name: /^Sin subestado/ })).toHaveCount(0)

  // A otra columna, sobre un grupo: cambian el estado y el subestado.
  await pendiente
    .getByRole('button', { name: `${marca} uno`, exact: true })
    .dragTo(enCurso.getByRole('button', { name: 'Sin subestado (1 tarea)' }))
  await expect(enCurso.getByRole('button', { name: 'Sin subestado (2 tareas)' })).toBeVisible()
  await expect(pendiente.getByRole('button', { name: `${bloqueado} (1 tarea)` })).toBeVisible()

  // Y se guarda en la API.
  const tareas = (await (await request.get('/api/v1/tareas')).json()) as {
    nombre: string
    subestado: string | null
    estado: { nombre: string } | null
  }[]
  const nuestras = tareas.filter((t) => t.nombre.startsWith(marca))
  expect(nuestras.map((t) => [t.nombre, t.estado?.nombre, t.subestado]).sort()).toEqual([
    [`${marca} dos`, 'Pendiente', bloqueado],
    [`${marca} tres`, 'En curso', null],
    [`${marca} uno`, 'En curso', null],
  ])
  await sinViolaciones(page)
})
