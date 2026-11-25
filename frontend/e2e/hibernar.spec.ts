import AxeBuilder from '@axe-core/playwright'
import type { APIRequestContext, Locator } from '@playwright/test'
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

// Crea por la API una tarea que vence dentro de tres días y devuelve su id.
async function crearTarea(
  request: APIRequestContext,
  nombre: string,
  grupoE2e: number,
): Promise<number> {
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre,
      descripcion: 'Para hibernar',
      fecha_creacion: isoLocal(new Date()),
      fecha_vencimiento: isoLocal(new Date(Date.now() + 3 * 24 * 60 * 60 * 1000)),
      grupo_estados_id: grupoE2e,
    },
  })
  expect(creada.status()).toBe(201)
  return ((await creada.json()) as { id: number }).id
}

// El detalle tiene dos cuentas atrás (cabecera y campo "Fecha de vencimiento"),
// que siempre muestran lo mismo: se devuelve su texto común.
async function textoContador(page: Page, nombre: string): Promise<string> {
  const textos = await page
    .getByRole('dialog', { name: nombre })
    .locator('[data-testid="contador-texto"]')
    .allInnerTexts()
  expect(textos).toHaveLength(2)
  expect(new Set(textos).size).toBe(1)
  return textos[0]!
}

// Ambas cuentas atrás del detalle están (o no) detenidas.
async function esperarDetenido(contador: Locator, detenido: boolean): Promise<void> {
  await expect(contador).toHaveCount(2)
  for (const indice of [0, 1]) {
    if (detenido) await expect(contador.nth(indice)).toHaveAttribute('data-congelado', 'true')
    else await expect(contador.nth(indice)).not.toHaveAttribute('data-congelado', 'true')
  }
}

test('hiberna una tarea con y sin comentario y la reanuda cuantas veces se quiera', async ({
  page,
  request,
  grupoE2e,
}) => {
  const nombre = `Hibernar ${Date.now()}`
  const id = await crearTarea(request, nombre, grupoE2e)

  await page.goto(`/tareas?tarea=${id}`)
  const detalle = page.getByRole('dialog', { name: nombre })
  await expect(detalle).toBeVisible()
  const contador = detalle.locator('[data-testid="contador-vencimiento"]')
  await esperarDetenido(contador, false)
  await expect(detalle.locator('[data-insignia-hibernada]')).toHaveCount(0)

  // Primera hibernación, con comentario.
  await detalle.getByRole('button', { name: `Hibernar la tarea ${nombre}` }).click()
  const dialogo = page.getByRole('alertdialog', { name: `Hibernar la tarea ${nombre}` })
  await expect(dialogo).toBeVisible()
  await dialogo
    .getByRole('textbox', { name: 'Comentario (opcional)' })
    .fill('Esperando respuesta del cliente')
  await dialogo.getByRole('button', { name: 'Hibernar', exact: true }).click()
  await expect(dialogo).toBeHidden()

  await expect(detalle.locator('[data-insignia-hibernada]')).toHaveText('Hibernada')
  await esperarDetenido(contador, true)
  const historial = detalle.getByRole('list', { name: 'Historial de comentarios' })
  await expect(historial).toContainText('Esperando respuesta del cliente')
  // Detenido: el texto no cambia aunque pasen los segundos.
  const congelado = await textoContador(page, nombre)
  await page.evaluate(() => new Promise((resolver) => setTimeout(resolver, 1500)))
  expect(await textoContador(page, nombre)).toBe(congelado)
  await page.screenshot({ path: 'e2e/capturas/hibernar-01-hibernada.png' })

  // La insignia también aparece en la fila de la lista.
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()
  await page.getByLabel('Buscar').fill(nombre)
  const fila = page.locator('[data-fila-tarea]', { hasText: nombre })
  await expect(fila.locator('[data-insignia-hibernada]')).toHaveText('Hibernada')
  await fila.locator('[data-nombre-tarea]').click()
  await expect(detalle).toBeVisible()

  // Reanudar: desaparece la insignia y el contador vuelve a contar.
  await detalle.getByRole('button', { name: `Reanudar la tarea ${nombre}` }).click()
  await expect(detalle.locator('[data-insignia-hibernada]')).toHaveCount(0)
  await esperarDetenido(contador, false)
  const enMarcha = await textoContador(page, nombre)
  await expect.poll(() => textoContador(page, nombre)).not.toBe(enMarcha)
  await expect(fila.locator('[data-insignia-hibernada]')).toHaveCount(0)

  // Segunda hibernación, sin comentario: no añade ninguno.
  await detalle.getByRole('button', { name: `Hibernar la tarea ${nombre}` }).click()
  await expect(dialogo).toBeVisible()
  await dialogo.getByRole('button', { name: 'Hibernar', exact: true }).click()
  await expect(dialogo).toBeHidden()
  await expect(detalle.locator('[data-insignia-hibernada]')).toHaveText('Hibernada')
  await esperarDetenido(contador, true)
  // Un solo comentario (el de la primera hibernación): los comentarios son los
  // `li` anidados en el de su día.
  await expect(historial.locator('li li')).toHaveCount(1)

  await detalle.getByRole('button', { name: `Reanudar la tarea ${nombre}` }).click()
  await expect(detalle.locator('[data-insignia-hibernada]')).toHaveCount(0)
  await esperarDetenido(contador, false)
})

const MODOS = [
  // `claseHtml`: el tema elegido se guarda en el navegador y sigue tras navegar.
  { modo: 'claro', preparar: async (_page: Page) => {}, claseHtml: /^(?!.*\bdark\b)/ },
  { modo: 'oscuro', preparar: activarModoOscuro, claseHtml: /\bdark\b/ },
] as const

for (const { modo, preparar, claseHtml } of MODOS) {
  test(`el diálogo de hibernar y la insignia son accesibles (modo ${modo})`, async ({
    page,
    request,
    grupoE2e,
  }) => {
    const nombre = `Hibernar a11y ${modo} ${Date.now()}`
    const id = await crearTarea(request, nombre, grupoE2e)
    const auditar = () =>
      new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .exclude('.vue-devtools__anchor-btn')
        .analyze()

    await page.goto('/tareas')
    await preparar(page)
    await page.goto(`/tareas?tarea=${id}`)
    await expect(page.locator('html')).toHaveClass(claseHtml)
    const detalle = page.getByRole('dialog', { name: nombre })
    await expect(detalle).toBeVisible()

    await detalle.getByRole('button', { name: `Hibernar la tarea ${nombre}` }).click()
    const dialogo = page.getByRole('alertdialog', { name: `Hibernar la tarea ${nombre}` })
    await expect(dialogo).toBeVisible()
    await dialogo.evaluate((elemento) =>
      Promise.all(elemento.getAnimations({ subtree: true }).map((a) => a.finished)),
    )
    await page.screenshot({ path: `e2e/capturas/hibernar-02-dialogo-${modo}.png` })
    expect((await auditar()).violations).toEqual([])

    await dialogo.getByRole('button', { name: 'Hibernar', exact: true }).click()
    await expect(dialogo).toBeHidden()
    await expect(detalle.locator('[data-insignia-hibernada]')).toHaveText('Hibernada')
    expect((await auditar()).violations).toEqual([])

    // En un móvil el pie con "Reanudar" no desborda la página.
    await page.setViewportSize({ width: 390, height: 844 })
    await expect(detalle.getByRole('button', { name: `Reanudar la tarea ${nombre}` })).toBeVisible()
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      ),
    ).toBe(false)
  })
}

test('hiberna y reanuda una tarea desde el tablero y desde el menú "⋯" del listado', async ({
  page,
  request,
  grupoE2e,
}) => {
  const nombre = `HibernarAtajos ${Date.now()}`
  const id = await crearTarea(request, nombre, grupoE2e)

  // Listado: el menú "⋯" de la fila abre el diálogo de hibernar.
  await page.goto('/tareas')
  await page.getByLabel('Buscar').fill(nombre)
  const fila = page.locator('[data-fila-tarea]', { hasText: nombre })
  await fila.getByRole('button', { name: `Acciones de la tarea ${nombre}` }).click()
  await page.getByRole('button', { name: `Hibernar la tarea ${nombre}` }).click()
  const dialogo = page.getByRole('alertdialog', { name: `Hibernar la tarea ${nombre}` })
  await dialogo.getByRole('button', { name: 'Hibernar', exact: true }).click()
  await expect(dialogo).toBeHidden()
  await expect(fila.locator('[data-insignia-hibernada]')).toBeVisible()
  const tras = await request.get('/api/v1/tareas')
  const guardada = ((await tras.json()) as { id: number; hibernada_desde: string | null }[]).find(
    (t) => t.id === id,
  )
  expect(guardada?.hibernada_desde).not.toBeNull()

  // Tablero: "Reanudar" la despierta sin diálogo, y "Hibernar" vuelve a abrirlo.
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({
    label: NOMBRE_GRUPO_E2E,
  })
  const tarjeta = page.locator('[data-tarjeta]', { hasText: nombre })
  await expect(tarjeta.locator('[data-insignia-hibernada]')).toBeVisible()
  await tarjeta.getByRole('button', { name: `Reanudar la tarea ${nombre}` }).click()
  await expect(tarjeta.locator('[data-insignia-hibernada]')).toHaveCount(0)
  await tarjeta.getByRole('button', { name: `Hibernar la tarea ${nombre}` }).click()
  await dialogo.getByRole('button', { name: 'Hibernar', exact: true }).click()
  await expect(tarjeta.locator('[data-insignia-hibernada]')).toBeVisible()
})
