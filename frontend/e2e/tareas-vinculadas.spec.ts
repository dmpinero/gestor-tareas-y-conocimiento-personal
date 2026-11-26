import AxeBuilder from '@axe-core/playwright'
import type { APIRequestContext } from '@playwright/test'
import { test, expect, NOMBRE_GRUPO_E2E, type Page } from './base'
import { activarModoOscuro } from './utilidades'

// Fecha y hora local sin zona ("YYYY-MM-DDTHH:MM:SS"), como las recibe la API.
function isoLocal(fecha: Date): string {
  const dos = (n: number) => String(n).padStart(2, '0')
  return (
    `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}` +
    `T${dos(fecha.getHours())}:${dos(fecha.getMinutes())}:${dos(fecha.getSeconds())}`
  )
}

// Crea por la API una tarea sin vencimiento y devuelve su id.
async function crearTarea(
  request: APIRequestContext,
  nombre: string,
  grupoE2e: number,
): Promise<number> {
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre,
      descripcion: 'Para relacionar',
      fecha_creacion: isoLocal(new Date()),
      grupo_estados_id: grupoE2e,
    },
  })
  expect(creada.status()).toBe(201)
  return ((await creada.json()) as { id: number }).id
}

async function vinculadasEnApi(request: APIRequestContext, id: number): Promise<number[]> {
  const tareas = (await (await request.get('/api/v1/tareas')).json()) as {
    id: number
    vinculadas: number[]
  }[]
  return tareas.find((tarea) => tarea.id === id)!.vinculadas
}

// El detalle se busca por su nombre exacto: el selector se llama
// "Relacionar tareas con …" y también contiene el nombre.
function detalleDe(page: Page, nombre: string) {
  return page.getByRole('dialog', { name: nombre, exact: true })
}

function seccionDe(page: Page, nombre: string) {
  return detalleDe(page, nombre).getByRole('region', { name: 'Tareas relacionadas' })
}

test('relaciona una tarea con dos a la vez, se ve en ambos sentidos y se quita', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = Date.now()
  const principal = `Vincular ${marca} principal`
  const primera = `Vincular ${marca} primera`
  const segunda = `Vincular ${marca} segunda`
  const idPrincipal = await crearTarea(request, principal, grupoE2e)
  const idPrimera = await crearTarea(request, primera, grupoE2e)
  const idSegunda = await crearTarea(request, segunda, grupoE2e)

  await page.goto(`/tareas?tarea=${idPrincipal}`)
  const seccion = seccionDe(page, principal)
  await expect(seccion).toContainText('Esta tarea no tiene tareas relacionadas.')

  // Se eligen las dos desde el selector, filtrando por la marca común.
  await seccion.getByRole('button', { name: 'Relacionar tareas' }).click()
  const selector = page.getByRole('dialog', { name: `Relacionar tareas con ${principal}` })
  await expect(selector).toBeVisible()
  // Sin filtrar (la base de e2e tiene muchas tareas), la lista se desplaza dentro
  // del diálogo y no tapa los botones.
  const lista = (await selector.locator('[data-lista-tareas]').boundingBox())!
  const cancelar = (await selector.getByRole('button', { name: 'Cancelar' }).boundingBox())!
  const dialogo = (await selector.boundingBox())!
  expect(lista.y + lista.height).toBeLessThanOrEqual(cancelar.y)
  expect(lista.y + lista.height).toBeLessThanOrEqual(dialogo.y + dialogo.height)
  await selector.getByRole('searchbox', { name: 'Buscar tarea' }).fill(`vinculár ${marca}`)
  await expect(selector.getByRole('checkbox')).toHaveCount(2)
  await expect(selector.getByRole('checkbox', { name: principal })).toHaveCount(0)
  await selector.getByRole('checkbox', { name: primera }).check()
  await selector.getByRole('checkbox', { name: segunda }).check()
  await selector.getByRole('button', { name: 'Relacionar (2)' }).click()
  await expect(selector).toBeHidden()

  await expect(seccion.locator('[data-vinculada]')).toHaveText([primera, segunda])
  expect(await vinculadasEnApi(request, idPrincipal)).toEqual([idPrimera, idSegunda])
  expect(await vinculadasEnApi(request, idSegunda)).toEqual([idPrincipal])
  await page.screenshot({ path: 'e2e/capturas/vinculadas-01-relacionadas.png' })

  // Pulsar una relacionada abre su detalle, que muestra la vuelta.
  await seccion.getByRole('button', { name: segunda, exact: true }).click()
  const seccionSegunda = seccionDe(page, segunda)
  await expect(seccionSegunda.locator('[data-vinculada]')).toHaveText([principal])

  // Quitar la relación desde la segunda la quita en ambos sentidos.
  await seccionSegunda.getByRole('button', { name: `Quitar relación con ${principal}` }).click()
  await expect(seccionSegunda).toContainText('Esta tarea no tiene tareas relacionadas.')
  expect(await vinculadasEnApi(request, idPrincipal)).toEqual([idPrimera])
  expect(await vinculadasEnApi(request, idSegunda)).toEqual([])
})

test('en el tablero, el botón de relacionadas despliega su árbol y abre cada una', async ({
  page,
  request,
  grupoE2e,
}) => {
  const marca = Date.now()
  const principal = `Arbol ${marca} principal`
  const otra = `Arbol ${marca} otra`
  const idPrincipal = await crearTarea(request, principal, grupoE2e)
  const idOtra = await crearTarea(request, otra, grupoE2e)
  const vinculada = await request.post(`/api/v1/tareas/${idPrincipal}/vinculadas`, {
    data: { ids: [idOtra] },
  })
  expect(vinculada.status()).toBe(200)

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({
    label: NOMBRE_GRUPO_E2E,
  })
  await page.getByLabel('Buscar').fill(`${marca}`)
  const tarjeta = page.locator('[data-tarjeta]', { hasText: principal })
  const boton = tarjeta.getByRole('button', { name: `1 tareas relacionadas de ${principal}` })
  await expect(boton).toHaveAttribute('aria-expanded', 'false')

  await boton.click()
  const arbol = page.getByRole('list', { name: `Tareas relacionadas de ${principal}` })
  await expect(arbol.locator('[data-relacionada]')).toHaveText([otra])
  await expect(boton).toHaveAttribute('aria-expanded', 'true')
  await page.screenshot({ path: 'e2e/capturas/vinculadas-03-arbol-tablero.png' })
  expect(
    (
      await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('.vue-devtools__anchor-btn')
        .analyze()
    ).violations,
  ).toEqual([])

  await arbol.getByRole('button', { name: otra }).click()
  await expect(detalleDe(page, otra)).toBeVisible()
})

const MODOS = [
  // `claseHtml`: el tema elegido se guarda en el navegador y sigue tras navegar.
  { modo: 'claro', preparar: async (_page: Page) => {}, claseHtml: /^(?!.*\bdark\b)/ },
  { modo: 'oscuro', preparar: activarModoOscuro, claseHtml: /\bdark\b/ },
] as const

for (const { modo, preparar, claseHtml } of MODOS) {
  test(`la sección y el selector de tareas relacionadas son accesibles (modo ${modo})`, async ({
    page,
    request,
    grupoE2e,
  }) => {
    const marca = Date.now()
    const principal = `Vincular a11y ${modo} ${marca}`
    const otra = `Vincular a11y otra ${modo} ${marca}`
    const idPrincipal = await crearTarea(request, principal, grupoE2e)
    const idOtra = await crearTarea(request, otra, grupoE2e)
    const vinculada = await request.post(`/api/v1/tareas/${idPrincipal}/vinculadas`, {
      data: { ids: [idOtra] },
    })
    expect(vinculada.status()).toBe(200)
    const auditar = () =>
      new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('.vue-devtools__anchor-btn')
        .analyze()

    await page.goto('/tareas')
    await preparar(page)
    await page.goto(`/tareas?tarea=${idPrincipal}`)
    await expect(page.locator('html')).toHaveClass(claseHtml)
    const seccion = seccionDe(page, principal)
    await expect(seccion.locator('[data-vinculada]')).toHaveText([otra])
    expect((await auditar()).violations).toEqual([])

    await seccion.getByRole('button', { name: 'Relacionar tareas' }).click()
    const selector = page.getByRole('dialog', { name: `Relacionar tareas con ${principal}` })
    await expect(selector).toBeVisible()
    await selector.evaluate((elemento) =>
      Promise.all(elemento.getAnimations({ subtree: true }).map((a) => a.finished)),
    )
    await page.screenshot({ path: `e2e/capturas/vinculadas-02-selector-${modo}.png` })
    expect((await auditar()).violations).toEqual([])

    // Escape cierra el selector sin relacionar nada.
    await page.keyboard.press('Escape')
    await expect(selector).toBeHidden()
    await expect(seccion.locator('[data-vinculada]')).toHaveText([otra])
  })
}
