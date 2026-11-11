import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

async function sinViolaciones(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze()
  expect(resultado.violations).toEqual([])
}

async function crearGrupoEnAjustes(page: Page, grupo: string, estados: string[]): Promise<void> {
  await page.goto('/ajustes')
  await page.getByRole('link', { name: 'Grupos de estados' }).click()
  await expect(page).toHaveURL(/\/ajustes\/grupos-estados$/)
  await page.getByRole('textbox', { name: 'Nombre del grupo' }).fill(grupo)
  await page.getByRole('button', { name: 'Añadir grupo' }).click()
  await expect(page.getByRole('heading', { name: grupo })).toBeVisible()
  for (const estado of estados) {
    await page.getByRole('textbox', { name: `Nuevo estado de ${grupo}` }).fill(estado)
    await page.getByRole('button', { name: `Añadir estado a ${grupo}` }).click()
    await expect(page.getByRole('list', { name: `Estados de ${grupo}` })).toContainText(estado)
  }
}

test('crea un grupo de estados, asigna una tarea y la mueve en el tablero', async ({ page }) => {
  const marca = Date.now()
  const grupo = `Grupo ${marca}`
  const tarea = `Tarea tablero ${marca}`
  await crearGrupoEnAjustes(page, grupo, ['Pendiente', 'En curso', 'Hecho'])

  // Reordenar: "Hecho" sube una posición.
  await page.getByRole('button', { name: `Subir estado Hecho de ${grupo}` }).click()
  await expect(
    page.getByRole('list', { name: `Estados de ${grupo}` }).getByRole('listitem'),
  ).toHaveText([/Pendiente/, /Hecho/, /En curso/])
  await page.screenshot({ path: 'e2e/capturas/grupos-01-ajustes.png' })
  await sinViolaciones(page)

  // Alta de la tarea con el grupo: empieza en el primer estado.
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  await ventana.getByPlaceholder('Nombre').fill(tarea)
  await ventana.getByPlaceholder('Descripción').fill('Con grupo de estados')
  await ventana.getByRole('combobox', { name: 'Grupo de estados' }).selectOption({ label: grupo })
  await ventana.getByRole('button', { name: 'Guardar' }).click()
  await expect(ventana).toBeHidden()

  // Tablero.
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await expect(page.getByRole('button', { name: 'Ver como tablero' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({ label: grupo })
  const columna = (estado: string) => page.getByRole('region', { name: `Estado ${estado}` })
  await expect(columna('Pendiente')).toContainText(tarea)
  await expect(columna('Hecho')).not.toContainText(tarea)

  // Mover con el teclado: "Mover a…".
  await columna('Pendiente')
    .getByRole('button', { name: `Mover a… (${tarea})` })
    .click()
  await page.getByRole('button', { name: 'En curso', exact: true }).click()
  await expect(columna('En curso')).toContainText(tarea)
  await expect(columna('Pendiente')).not.toContainText(tarea)
  await expect(
    columna('En curso').getByRole('button', { name: `Mover a… (${tarea})` }),
  ).toBeFocused()

  // Mover arrastrando.
  await columna('En curso')
    .getByRole('button', { name: tarea, exact: true })
    .dragTo(columna('Hecho'))
  await expect(columna('Hecho')).toContainText(tarea)
  await page.screenshot({ path: 'e2e/capturas/grupos-02-tablero.png' })
  await sinViolaciones(page)

  // Se guarda y la vista se recuerda al recargar.
  await page.reload()
  await expect(page.getByRole('button', { name: 'Ver como tablero' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({ label: grupo })
  await expect(columna('Hecho')).toContainText(tarea)

  // El detalle muestra el grupo y el estado.
  await columna('Hecho').getByRole('button', { name: tarea, exact: true }).click()
  const detalle = page.getByRole('dialog', { name: tarea })
  await expect(detalle).toContainText(grupo)
  await expect(detalle).toContainText('Hecho')
  await page.keyboard.press('Escape')

  await page.getByRole('button', { name: 'Ver como lista' }).click()
  await expect(page.locator('tr', { hasText: tarea })).toHaveCount(1)
})

test('al borrar un estado con tareas pide a qué estado moverlas', async ({ page, request }) => {
  const marca = Date.now()
  const grupo = `Borrado ${marca}`
  const tarea = `Tarea a mover ${marca}`
  await crearGrupoEnAjustes(page, grupo, ['Uno', 'Dos'])
  const grupos = (await (await request.get('/api/v1/grupos-estados')).json()) as {
    id: number
    nombre: string
  }[]
  const id = grupos.find((g) => g.nombre === grupo)!.id
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre: tarea,
      descripcion: 'd',
      fecha_creacion: '2026-01-01T09:00:00',
      grupo_estados_id: id,
    },
  })
  expect(creada.status()).toBe(201)

  await page.reload()
  await page.getByRole('button', { name: `Eliminar estado Uno de ${grupo}` }).click()
  const confirmar = page.getByRole('alertdialog', { name: '¿Eliminar el estado Uno?' })
  await expect(confirmar).toContainText('Tiene 1 tarea')
  await confirmar
    .getByRole('combobox', { name: 'Mover las tareas a' })
    .selectOption({ label: 'Dos' })
  await sinViolaciones(page)
  await confirmar.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByRole('list', { name: `Estados de ${grupo}` })).not.toContainText('Uno')

  const lista = (await (await request.get('/api/v1/tareas')).json()) as {
    nombre: string
    estado: { nombre: string } | null
  }[]
  expect(lista.find((t) => t.nombre === tarea)!.estado?.nombre).toBe('Dos')
})

test('el tablero no desborda la página en un móvil', async ({ page }) => {
  const grupo = `Móvil ${Date.now()}`
  await crearGrupoEnAjustes(page, grupo, ['A', 'B', 'C', 'D'])
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Ver como tablero' }).click()
  await page.getByRole('combobox', { name: 'Grupo del tablero' }).selectOption({ label: grupo })
  await expect(page.getByRole('region', { name: 'Estado D' })).toBeAttached()
  const desborda = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(desborda).toBe(false)
  await page.screenshot({ path: 'e2e/capturas/grupos-03-tablero-movil.png' })
})

test('muestra las tareas en un calendario según su fecha de vencimiento', async ({
  page,
  request,
}) => {
  const tarea = `Calendario ${Date.now()}`
  // Vence el día 15 del mes actual a las 18:30 (hora local, sin zona).
  const hoy = new Date()
  const mes = String(hoy.getMonth() + 1).padStart(2, '0')
  const vencimiento = `${hoy.getFullYear()}-${mes}-15T18:30:00`
  const creada = await request.post('/api/v1/tareas', {
    data: {
      nombre: tarea,
      descripcion: 'En el calendario',
      fecha_creacion: `${hoy.getFullYear()}-${mes}-01T09:00:00`,
      fecha_vencimiento: vencimiento,
    },
  })
  expect(creada.status()).toBe(201)

  await page.goto('/tareas')
  // La búsqueda también filtra el calendario: así el día solo tiene esta tarea
  // aunque otras pruebas hayan dejado tareas que vencen el mismo día.
  await page.getByLabel('Buscar').fill(tarea)
  await page.getByRole('button', { name: 'Ver como calendario' }).click()
  await expect(page.getByRole('button', { name: 'Ver como calendario' })).toHaveAttribute(
    'aria-pressed',
    'true',
  )
  const nombreDia = new Intl.DateTimeFormat('es-ES', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(hoy.getFullYear(), hoy.getMonth(), 15))
  const dia = page.getByRole('group', { name: nombreDia, exact: true })
  await expect(dia.getByRole('button', { name: `18:30 ${tarea}` })).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/grupos-04-calendario.png' })
  await sinViolaciones(page)

  // Navegación: el mes siguiente no la muestra; "Hoy" vuelve.
  await page.getByRole('button', { name: 'Mes siguiente' }).click()
  await expect(page.getByRole('button', { name: `18:30 ${tarea}` })).toHaveCount(0)
  await page.getByRole('button', { name: 'Hoy' }).click()
  await dia.getByRole('button', { name: `18:30 ${tarea}` }).click()
  await expect(page.getByRole('dialog', { name: tarea })).toBeVisible()
  await page.keyboard.press('Escape')

  // En un móvil, agenda sin desbordar.
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(page.getByRole('button', { name: `18:30 ${tarea}` })).toBeVisible()
  const desborda = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  )
  expect(desborda).toBe(false)
})
