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

test('el panel "Crear tarea" no tiene violaciones de accesibilidad en modo claro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/tareas')
  const resultado = await auditarPanelCrearTarea(page)
  expect(resultado.violations).toEqual([])
})

test('el panel "Crear tarea" no tiene violaciones de accesibilidad en modo oscuro (WCAG 2.1 AA)', async ({
  page,
}) => {
  await page.goto('/tareas')
  await activarModoOscuro(page)
  const resultado = await auditarPanelCrearTarea(page)
  expect(resultado.violations).toEqual([])
})
