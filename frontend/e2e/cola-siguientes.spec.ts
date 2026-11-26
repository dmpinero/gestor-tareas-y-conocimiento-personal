import AxeBuilder from '@axe-core/playwright'
import type { APIRequestContext } from '@playwright/test'
import { test, expect, type Page } from './base'
import { activarModoOscuro } from './utilidades'

// Fecha y hora local sin zona ("YYYY-MM-DDTHH:MM:SS"), como las recibe la API.
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
      descripcion: 'Para la cola',
      fecha_creacion: isoLocal(new Date()),
      grupo_estados_id: grupoE2e,
      ...extra,
    },
  })
  expect(creada.status()).toBe(201)
  return ((await creada.json()) as { id: number }).id
}

async function colaEnApi(request: APIRequestContext): Promise<number[]> {
  const cola = (await (await request.get('/api/v1/siguientes')).json()) as { tarea_id: number }[]
  return cola.map((entrada) => entrada.tarea_id)
}

// La cola es única para toda la aplicación: cada test deja la que había y se
// lleva por delante solo sus tareas.
async function vaciarCola(request: APIRequestContext, ids: number[]): Promise<void> {
  for (const id of ids) await request.delete(`/api/v1/siguientes/${id}`)
}

// Comparten la cola: dentro de este archivo, uno detrás de otro.
test.describe.configure({ mode: 'serial' })

function panel(page: Page) {
  return page.getByRole('region', { name: 'A continuación' })
}

test('añade tareas a la cola, la reordena y pasa a la siguiente desde la barra superior', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = Date.now()
  const primera = `Cola ${marca} primera`
  const segunda = `Cola ${marca} segunda`
  const idPrimera = await crearTarea(request, primera, grupoE2e)
  const idSegunda = await crearTarea(request, segunda, grupoE2e)
  const previa = await colaEnApi(request)
  await vaciarCola(request, previa)
  await request.delete('/api/v1/foco')

  try {
    // Desde el detalle de cada tarea.
    for (const [id, nombre] of [
      [idPrimera, primera],
      [idSegunda, segunda],
    ] as const) {
      await page.goto(`/tareas?tarea=${id}`)
      const detalle = page.getByRole('dialog', { name: nombre, exact: true })
      await detalle.getByRole('button', { name: /Añadir a siguientes/ }).click()
      await expect(detalle.getByRole('button', { name: /Quitar de siguientes/ })).toBeVisible()
    }
    expect(await colaEnApi(request)).toEqual([idPrimera, idSegunda])

    // En Inicio se ven en orden y se reordenan.
    await page.goto('/')
    const filas = panel(page).locator('[data-fila-siguiente]')
    await expect(filas).toHaveCount(2)
    await expect(filas.nth(0)).toContainText(primera)
    await panel(page)
      .getByRole('button', { name: `Bajar ${primera}` })
      .click()
    await expect(filas.nth(0)).toContainText(segunda)
    expect(await colaEnApi(request)).toEqual([idSegunda, idPrimera])
    // También arrastrando con el ratón (ida y vuelta).
    await filas.nth(1).dragTo(filas.nth(0))
    await expect(filas.nth(0)).toContainText(primera)
    expect(await colaEnApi(request)).toEqual([idPrimera, idSegunda])
    await filas.nth(1).dragTo(filas.nth(0))
    await expect(filas.nth(0)).toContainText(segunda)
    expect(await colaEnApi(request)).toEqual([idSegunda, idPrimera])
    await page.screenshot({ path: 'e2e/capturas/siguientes-01-inicio.png' })

    // En el desplegable de la barra superior también se arrastran.
    await page.locator('[data-siguientes]').click()
    const enDesplegable = page.locator('[data-siguiente]')
    await enDesplegable.nth(1).dragTo(enDesplegable.nth(0))
    await expect(enDesplegable.nth(0)).toContainText(primera)
    expect(await colaEnApi(request)).toEqual([idPrimera, idSegunda])
    await enDesplegable.nth(1).dragTo(enDesplegable.nth(0))
    await expect(enDesplegable.nth(0)).toContainText(segunda)
    expect(await colaEnApi(request)).toEqual([idSegunda, idPrimera])

    // Sin foco, la barra superior ofrece pasar a la siguiente.
    await page.locator('[data-pasar-siguiente]').click()
    await expect(page.locator('[data-indicador-foco]')).toContainText(segunda)
    await expect(filas).toHaveCount(1)
    await expect(filas.nth(0)).toContainText(primera)
    expect(await colaEnApi(request)).toEqual([idPrimera])

    // Quitar desde el panel.
    await panel(page)
      .getByRole('button', { name: `Quitar ${primera} de siguientes` })
      .click()
    await expect(panel(page)).toContainText('No hay tareas en la cola.')
    expect(await colaEnApi(request)).toEqual([])
  } finally {
    await vaciarCola(request, [idPrimera, idSegunda])
    await request.delete('/api/v1/foco')
  }
})

test('una tarea muy vencida aparece en las sugerencias y se sube a la cola', async ({
  page,
  request,
  grupoE2e,
}) => {
  const nombre = `Cola ${Date.now()} vencida`
  const id = await crearTarea(request, nombre, grupoE2e, {
    fecha_creacion: '1999-12-01T09:00:00',
    fecha_vencimiento: '2000-01-01T09:00:00',
    prioridad: 1,
  })
  try {
    await page.goto('/')
    const sugerencia = page
      .getByRole('region', { name: 'Sugerencias' })
      .locator('[data-sugerencia]', { hasText: nombre })
    await expect(sugerencia).toBeVisible()
    await sugerencia.getByRole('button', { name: /Añadir a siguientes/ }).click()
    await expect(panel(page).locator('[data-fila-siguiente]', { hasText: nombre })).toBeVisible()
    await expect(sugerencia).toHaveCount(0)
    expect(await colaEnApi(request)).toContain(id)
  } finally {
    await vaciarCola(request, [id])
    await request.delete(`/api/v1/tareas/${id}`)
  }
})

test('el buscador añade varias tareas a la cola desde Inicio y desde la barra superior', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = Date.now()
  const nombres = [`Buscar ${marca} uno`, `Buscar ${marca} dos`, `Buscar ${marca} tres`]
  const ids: number[] = []
  for (const nombre of nombres) ids.push(await crearTarea(request, nombre, grupoE2e))
  const previa = await colaEnApi(request)
  await vaciarCola(request, previa)
  try {
    await page.goto('/')
    await panel(page).getByRole('button', { name: 'Buscar tareas' }).click()
    const dialogo = page.getByRole('dialog', { name: 'Añadir a siguientes' })
    await expect(dialogo).toBeVisible()
    await dialogo.getByRole('searchbox', { name: 'Buscar tarea' }).fill(`búscar ${marca}`)
    await expect(dialogo.getByRole('checkbox')).toHaveCount(3)
    // En el orden en que se marcan.
    await dialogo.getByRole('checkbox', { name: nombres[1] }).check()
    await dialogo.getByRole('checkbox', { name: nombres[0] }).check()
    await dialogo.evaluate((elemento) =>
      Promise.all(elemento.getAnimations({ subtree: true }).map((a) => a.finished)),
    )
    const auditoria = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .exclude('.vue-devtools__anchor-btn')
      .analyze()
    expect(auditoria.violations).toEqual([])
    await page.screenshot({ path: 'e2e/capturas/siguientes-03-buscador.png' })
    await dialogo.getByRole('button', { name: 'Añadir (2)' }).click()
    await expect(dialogo).toBeHidden()
    await expect(panel(page).locator('[data-fila-siguiente]')).toHaveCount(2)
    expect(await colaEnApi(request)).toEqual([ids[1], ids[0]])

    // Desde el desplegable: ya no ofrece las de la cola.
    await page.locator('[data-siguientes]').click()
    await page.locator('[data-buscar-siguientes]').last().click()
    await expect(dialogo).toBeVisible()
    await dialogo.getByRole('searchbox', { name: 'Buscar tarea' }).fill(`${marca}`)
    await expect(dialogo.getByRole('checkbox')).toHaveCount(1)
    await dialogo.getByRole('checkbox', { name: nombres[2] }).check()
    await dialogo.getByRole('button', { name: 'Añadir (1)' }).click()
    await expect(dialogo).toBeHidden()
    expect(await colaEnApi(request)).toEqual([ids[1], ids[0], ids[2]])
  } finally {
    await vaciarCola(request, ids)
  }
})

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`el panel y el desplegable de siguientes son accesibles (modo ${modo})`, async ({
    page,
    request,
    grupoE2e,
  }) => {
    const nombre = `Cola a11y ${modo} ${Date.now()}`
    const id = await crearTarea(request, nombre, grupoE2e)
    expect((await request.post('/api/v1/siguientes', { data: { tarea_id: id } })).status()).toBe(
      200,
    )
    const auditar = () =>
      new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('.vue-devtools__anchor-btn')
        .analyze()
    try {
      await page.goto('/')
      await preparar(page)
      await page.goto('/')
      await expect(panel(page).locator('[data-fila-siguiente]', { hasText: nombre })).toBeVisible()
      expect((await auditar()).violations).toEqual([])

      await page.locator('[data-siguientes]').click()
      const contenido = page.locator('[data-slot="popover-content"]')
      await expect(contenido).toBeVisible()
      await contenido.evaluate((elemento) =>
        Promise.all(elemento.getAnimations({ subtree: true }).map((a) => a.finished)),
      )
      await page.screenshot({ path: `e2e/capturas/siguientes-02-desplegable-${modo}.png` })
      expect((await auditar()).violations).toEqual([])
    } finally {
      await vaciarCola(request, [id])
    }
  })
}
