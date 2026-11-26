import AxeBuilder from '@axe-core/playwright'
import type { APIRequestContext } from '@playwright/test'
import { test, expect, type Page } from './base'
import { activarModoOscuro } from './utilidades'

async function crearTarea(
  request: APIRequestContext,
  nombre: string,
  extra: Record<string, unknown> = {},
): Promise<void> {
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre,
      descripcion: `${nombre}: una descripción bastante larga para comprobar que la fila no crece de más`,
      fecha_creacion: '2026-11-16T12:51:56',
      ...extra,
    },
  })
  expect(creada.status()).toBe(201)
}

const APLICAR_MODO: Record<'claro' | 'oscuro', (page: Page) => Promise<void>> = {
  claro: async () => {},
  oscuro: activarModoOscuro,
}

async function sinViolaciones(page: Page, selector: string): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .include(selector)
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(resultado.violations).toEqual([])
}

for (const modo of ['claro', 'oscuro'] as const) {
  test(`en un móvil la lista muestra tarjetas sin desbordar y accesibles (modo ${modo})`, async ({
    page,
    request,
  }) => {
    const marca = `Tarjeta${Date.now()}`
    await crearTarea(request, `${marca} con un nombre largo que debe leerse entero`, {
      prioridad: 2,
      subestado: 'Pendiente recibir respuesta del cliente',
      etiquetas: ['Backend'],
    })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto('/tareas')
    await APLICAR_MODO[modo](page)
    await page.getByLabel('Buscar').fill(marca)

    const tarjeta = page.locator('[data-tarjeta-tarea]', { hasText: marca })
    await expect(tarjeta).toBeVisible()
    await expect(page.locator('[data-testid="superficie-tabla"] table')).toHaveCount(0)
    // El nombre usa casi todo el ancho de la tarjeta (antes se partía letra a letra).
    const anchoNombre = (await tarjeta.locator('[data-nombre-tarea]').boundingBox())!.width
    expect(anchoNombre).toBeGreaterThan(200)
    const sinScroll = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    )
    expect(sinScroll).toBe(true)
    await page.screenshot({ path: `e2e/capturas/lista-tarjetas-${modo}.png` })
    await sinViolaciones(page, '[data-lista-tarjetas]')

    await tarjeta.click({ position: { x: 20, y: 80 } })
    await expect(page.getByRole('dialog', { name: new RegExp(marca) })).toBeVisible()
  })
}

test('al desplazar la tabla en horizontal la columna Nombre se queda a la vista', async ({
  page,
  request,
}) => {
  const marca = `Fija${Date.now()}`
  await crearTarea(request, `${marca} tarea`)

  await page.setViewportSize({ width: 1024, height: 800 })
  await page.goto('/tareas')
  await page.getByLabel('Buscar').fill(marca)
  const nombre = page.locator('[data-fila-tarea] [data-nombre-tarea]', { hasText: marca })
  await expect(nombre).toBeVisible()
  const antes = (await nombre.boundingBox())!.x

  const desplazable = page.locator('[data-testid="superficie-tabla"] table').locator('..')
  const desplazado = await desplazable.evaluate((elemento) => {
    elemento.scrollLeft = 500
    return elemento.scrollLeft
  })
  expect(desplazado).toBeGreaterThan(0)
  // Salvo el medio borde colapsado de la tabla (≤ 2 px), no se mueve.
  await expect
    .poll(async () => Math.abs((await nombre.boundingBox())!.x - antes))
    .toBeLessThanOrEqual(2)
  // Las acciones, fijas a la derecha, siguen pulsables.
  await page
    .getByRole('button', { name: `Acciones de la tarea ${marca} tarea`, exact: true })
    .click()
  await expect(page.getByRole('button', { name: `Editar tarea ${marca} tarea` })).toBeVisible()
  await page.keyboard.press('Escape')
  // La fecha de creación se ve corta.
  await expect(
    page.locator('[data-fila-tarea]', { hasText: marca }).locator('[data-fecha-creacion]'),
  ).toHaveText('16 nov16/11/2026 12:51:56')
})

for (const modo of ['claro', 'oscuro'] as const) {
  test(`el calendario con "Ocultar completadas" y el aviso pulsable es accesible (modo ${modo})`, async ({
    page,
  }) => {
    await page.goto('/tareas')
    await APLICAR_MODO[modo](page)
    await page.getByRole('button', { name: 'Ver como calendario' }).click()

    const ocultar = page.getByRole('button', { name: 'Ocultar completadas' })
    await ocultar.click()
    await expect(ocultar).toHaveAttribute('aria-pressed', 'true')
    await sinViolaciones(page, '[data-testid="calendario-tareas"]')
    await ocultar.click()
    await expect(ocultar).toHaveAttribute('aria-pressed', 'false')
  })
}
