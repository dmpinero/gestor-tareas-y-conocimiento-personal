import { test, expect, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { activarModoOscuro, SECCIONES } from './utilidades'

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
