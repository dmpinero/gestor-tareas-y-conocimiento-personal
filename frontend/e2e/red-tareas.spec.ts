import AxeBuilder from '@axe-core/playwright'
import type { APIRequestContext } from '@playwright/test'
import { test, expect, type Page } from './base'
import { activarModoOscuro } from './utilidades'

function isoLocal(fecha: Date): string {
  const dos = (n: number) => String(n).padStart(2, '0')
  return (
    `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}` +
    `T${dos(fecha.getHours())}:${dos(fecha.getMinutes())}:${dos(fecha.getSeconds())}`
  )
}

async function crearTarea(
  request: APIRequestContext,
  nombre: string,
  grupoE2e: number,
  extra: Record<string, unknown> = {},
): Promise<number> {
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre,
      descripcion: 'Para la red',
      fecha_creacion: isoLocal(new Date()),
      grupo_estados_id: grupoE2e,
      ...extra,
    },
  })
  expect(creada.status()).toBe(201)
  return ((await creada.json()) as { id: number }).id
}

// Tres tareas: dos comparten etiqueta, otras dos están relacionadas.
async function prepararRed(request: APIRequestContext, grupoE2e: number) {
  const marca = Date.now()
  const etiqueta = `red-${marca}`
  const nombres = [`Red ${marca} uno`, `Red ${marca} dos`, `Red ${marca} tres`]
  const uno = await crearTarea(request, nombres[0]!, grupoE2e, { etiquetas: [etiqueta] })
  const dos = await crearTarea(request, nombres[1]!, grupoE2e, { etiquetas: [etiqueta] })
  const tres = await crearTarea(request, nombres[2]!, grupoE2e)
  const vinculada = await request.post(`/api/v1/tareas/${dos}/vinculadas`, {
    data: { ids: [tres] },
  })
  expect(vinculada.status()).toBe(200)
  return { marca, etiqueta, nombres, ids: [uno, dos, tres] as const }
}

async function abrirRed(page: Page, marca: number): Promise<void> {
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como red' }).click()
  await page.getByLabel('Buscar').fill(`${marca}`)
}

test('la red une las tareas por su etiqueta y por estar relacionadas, y abre su detalle', async ({
  page,
  request,
  grupoE2e,
}) => {
  const { marca, etiqueta, nombres, ids } = await prepararRed(request, grupoE2e)
  await abrirRed(page, marca)

  const red = page.getByRole('region', { name: 'Red de tareas' })
  await expect(red.locator('[data-tipo="tarea"][data-nodo]')).toHaveCount(3)
  const nodoEtiqueta = red.locator(`[data-nodo="etiqueta:${etiqueta}"]`)
  await expect(nodoEtiqueta).toHaveAttribute('aria-label', `Etiqueta ${etiqueta}: 2 tareas`)
  await expect(red.locator(`[data-arista="tarea:${ids[1]}|tarea:${ids[2]}"]`)).toHaveCount(1)
  await page.screenshot({ path: 'e2e/capturas/red-01-claro.png' })

  // Fijar la etiqueta resalta sus tareas y atenúa la otra.
  await nodoEtiqueta.click()
  await expect(nodoEtiqueta).toHaveAttribute('aria-pressed', 'true')
  await expect(red.locator(`[data-nodo="tarea:${ids[2]}"]`)).toHaveAttribute(
    'data-atenuado',
    'true',
  )
  await expect(red.locator(`[data-nodo="tarea:${ids[0]}"]`)).toHaveAttribute(
    'data-atenuado',
    'false',
  )
  await nodoEtiqueta.click()

  // Quitar las etiquetas deja solo la unión de las relacionadas.
  await red.getByLabel('Etiquetas').uncheck()
  await expect(nodoEtiqueta).toHaveCount(0)
  await expect(red.locator(`[data-arista="tarea:${ids[1]}|tarea:${ids[2]}"]`)).toHaveCount(1)
  await red.getByLabel('Etiquetas').check()

  // El zoom cambia la vista; con el teclado se abre el detalle.
  const vista = red.locator('[data-testid="vista-red"]')
  const antes = await vista.getAttribute('transform')
  await red.getByRole('button', { name: 'Acercar' }).click()
  await expect(vista).not.toHaveAttribute('transform', antes ?? '')
  await red.locator(`[data-nodo="tarea:${ids[0]}"]`).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('dialog', { name: nombres[0], exact: true })).toBeVisible()
})

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`la vista de red es accesible y cabe en un móvil (modo ${modo})`, async ({
    page,
    request,
    grupoE2e,
  }) => {
    const { marca } = await prepararRed(request, grupoE2e)
    await page.goto('/tareas')
    await preparar(page)
    await abrirRed(page, marca)
    const red = page.getByRole('region', { name: 'Red de tareas' })
    await expect(red.locator('[data-tipo="tarea"][data-nodo]')).toHaveCount(3)
    const auditar = async () =>
      (
        await new AxeBuilder({ page })
          .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
          .exclude('.vue-devtools__anchor-btn')
          .analyze()
      ).violations
    expect(await auditar()).toEqual([])

    await page.setViewportSize({ width: 390, height: 844 })
    await expect(red.locator('[data-tipo="tarea"][data-nodo]')).toHaveCount(3)
    const anchoPagina = await page.evaluate(() => document.documentElement.scrollWidth)
    expect(anchoPagina).toBeLessThanOrEqual(390)
    await page.screenshot({ path: `e2e/capturas/red-02-movil-${modo}.png` })
    expect(await auditar()).toEqual([])
  })
}
