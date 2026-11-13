import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { activarModoOscuro, SECCIONES } from './utilidades'

// Las acciones de cada fila de la lista (Editar, Ver detalle, Eliminar) están en
// su menú "⋯", con el mismo nombre accesible que tenían como botones sueltos.
async function accionDeFila(page: Page, nombre: string, accion: string): Promise<void> {
  await page.getByRole('button', { name: `Acciones de la tarea ${nombre}`, exact: true }).click()
  await page.getByRole('button', { name: `${accion} ${nombre}`, exact: true }).click()
}

async function auditarPagina(page: Page) {
  return (
    new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      // El panel de Vue Devtools solo se inyecta en modo desarrollo y no forma
      // parte de la aplicación real; se excluye para no analizar una herramienta
      // de terceros ajena a nuestro código.
      .exclude('.vue-devtools__anchor-btn')
      .analyze()
  )
}

for (const { ruta } of SECCIONES) {
  test(`${ruta} no tiene violaciones de accesibilidad en modo claro (WCAG 2.1 AA)`, async ({
    page,
  }) => {
    await page.goto(ruta)
    const resultado = await auditarPagina(page)
    expect(resultado.violations).toEqual([])
  })

  test(`${ruta} no tiene violaciones de accesibilidad en modo oscuro (WCAG 2.1 AA)`, async ({
    page,
  }) => {
    await page.goto(ruta)
    await activarModoOscuro(page)
    const resultado = await auditarPagina(page)
    expect(resultado.violations).toEqual([])
  })
}

// Regresión: en modo oscuro el botón "Cancelar" (variante `destructive`) del
// panel de tareas tenía un contraste de 2,88:1. Las auditorías de arriba no
// abren el panel, así que no lo detectaban.
async function auditarPanelCrearTarea(page: Page) {
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog', { name: 'Crear tarea' })
  await expect(panel).toHaveAttribute('data-state', 'open')
  // Se espera a que acaben las animaciones de entrada para no medir colores a medias.
  await panel.evaluate((elemento) =>
    Promise.all(elemento.getAnimations({ subtree: true }).map((animacion) => animacion.finished)),
  )
  return auditarPagina(page)
}

test('la ventana "Crear tarea" no tiene violaciones de accesibilidad en modo claro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/tareas')
  const resultado = await auditarPanelCrearTarea(page)
  expect(resultado.violations).toEqual([])
})

test('la ventana "Crear tarea" no tiene violaciones de accesibilidad en modo oscuro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/tareas')
  await activarModoOscuro(page)
  const resultado = await auditarPanelCrearTarea(page)
  expect(resultado.violations).toEqual([])
})

// El historial de cambios se lee de la API de GitHub; se simula para no depender
// de la red ni del límite de peticiones. Incluye HTML peligroso para comprobar
// que se sanea antes de mostrarlo.
const RELEASES_SIMULADAS = [
  {
    tag_name: 'v9.9.9',
    name: 'v9.9.9',
    body: '### ✨ Novedades\n\n* una novedad\n\n<img src="x" alt="" onerror="window.__inyectado = true">',
    published_at: '2026-11-10T00:00:00Z',
    html_url: 'https://github.com/',
  },
]

async function auditarHistorialDeCambios(page: Page) {
  // Rutas separadas para la última release y el historial (Playwright usa la
  // última ruta registrada que coincide).
  await page.route('https://api.github.com/**/releases*', (ruta) =>
    ruta.fulfill({ json: RELEASES_SIMULADAS }),
  )
  await page.route('https://api.github.com/**/releases/latest', (ruta) =>
    ruta.fulfill({ json: RELEASES_SIMULADAS[0] }),
  )
  await page.getByRole('button', { name: 'Ayuda: historial de cambios' }).click()
  await page.getByRole('button', { name: 'Historial de cambios', exact: true }).click()
  const modal = page.getByRole('dialog', { name: 'Historial de cambios' })
  await expect(modal.getByText('una novedad')).toBeVisible()
  await modal.evaluate((elemento) =>
    Promise.all(elemento.getAnimations().map((animacion) => animacion.finished)),
  )
  const inyectado = await page.evaluate(() => (window as { __inyectado?: boolean }).__inyectado)
  expect(inyectado).toBeUndefined()
  return auditarPagina(page)
}

test('el historial de cambios no tiene violaciones de accesibilidad en modo claro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/')
  const resultado = await auditarHistorialDeCambios(page)
  expect(resultado.violations).toEqual([])
})

test('el historial de cambios no tiene violaciones de accesibilidad en modo oscuro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/')
  await activarModoOscuro(page)
  const resultado = await auditarHistorialDeCambios(page)
  expect(resultado.violations).toEqual([])
})

// Regresión: el botón de comentarios de una subtarea con comentarios mostraba su
// número fuera del nombre accesible (WCAG 2.5.3, label-content-name-mismatch).
const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`el detalle con los comentarios de una subtarea abiertos no tiene violaciones de accesibilidad en modo ${modo} (WCAG 2.1 AA)`, async ({
    page,
    request,
  }) => {
    const nombre = `Accesible ${modo} ${Date.now()}`
    const creada = await request.post('/api/v1/tareas', {
      data: { nombre, descripcion: 'Auditoría', fecha_creacion: '2026-01-01T09:00:00' },
    })
    const { id } = (await creada.json()) as { id: number }
    const subtarea = await request.post(`/api/v1/tareas/${id}/subtareas`, {
      data: { nombre: 'Auditar' },
    })
    const { subtareas } = (await subtarea.json()) as { subtareas: { id: number }[] }
    const ruta = `/api/v1/tareas/${id}/subtareas/${subtareas[0]!.id}/comentarios`
    expect((await request.post(ruta, { data: { texto: 'Primero' } })).status()).toBe(201)
    expect(
      (
        await request.post(`/api/v1/tareas/${id}/comentarios`, { data: { texto: 'De la tarea' } })
      ).status(),
    ).toBe(201)

    await page.goto('/tareas')
    await preparar(page)
    await accionDeFila(page, nombre, 'Ver detalle de la tarea')
    const detalle = page.getByRole('dialog', { name: nombre })
    const boton = detalle.getByRole('button', { name: 'Comentarios de la subtarea Auditar: 1' })
    await expect(boton).toBeVisible()
    await boton.click()
    await expect(detalle.getByTestId('comentarios-subtarea')).toContainText('Primero')
    // Espera a que terminen las animaciones de apertura (las infinitas no cuentan).
    await detalle.evaluate((elemento) =>
      Promise.all(
        elemento
          .getAnimations({ subtree: true })
          .filter((animacion) => animacion.effect?.getTiming().iterations !== Infinity)
          .map((animacion) => animacion.finished),
      ),
    )

    const resultado = await auditarPagina(page)
    expect(resultado.violations).toEqual([])
  })
}

// Regresión: el contador de filtros activos estaba dentro del botón que pliega
// los filtros y su texto no formaba parte del nombre (WCAG 2.5.3).
test('el panel de filtros con filtros activos no tiene violaciones de accesibilidad (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/tareas')
  await page.getByLabel('Buscar').fill('zzz')
  await page.getByRole('button', { name: 'Filtrar', exact: true }).click()
  await page.getByRole('radio', { name: 'Completadas', exact: true }).check()
  await expect(page.getByTestId('filtros-activos')).toHaveText('2 activos')
  const resultado = await auditarPagina(page)
  expect(resultado.violations).toEqual([])
})
