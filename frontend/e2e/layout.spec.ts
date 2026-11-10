import { test, expect } from '@playwright/test'
import { activarModoOscuro, SECCIONES } from './utilidades'

test('el panel de navegación colapsa y expande, y resalta la sección activa', async ({ page }) => {
  await page.goto('/')
  await page.screenshot({ path: 'e2e/capturas/layout-01-inicio.png' })

  await expect(page.getByRole('link', { name: 'Tareas' })).toBeVisible()

  await page.goto('/conocimiento')
  await expect(page.getByRole('link', { name: 'Conocimiento' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(page.getByRole('link', { name: 'Inicio' })).not.toHaveAttribute(
    'aria-current',
    'page',
  )

  const botonColapsar = page.getByRole('button', { name: 'Contraer panel de navegación' })
  const botonExpandir = page.getByRole('button', { name: 'Expandir panel de navegación' })

  // Sin preferencia guardada el panel arranca colapsado.
  await expect(botonExpandir).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/layout-02-sidebar-colapsado.png' })

  await botonExpandir.click()
  await expect(botonColapsar).toBeVisible()

  await botonColapsar.click()
  await expect(botonExpandir).toBeVisible()
  await botonExpandir.click()
  await expect(botonColapsar).toBeVisible()
  await expect(page.getByRole('link', { name: 'Conocimiento' })).toContainText('Conocimiento')
})

for (const { ruta, etiqueta } of SECCIONES) {
  test(`el enlace "${etiqueta}" navega a ${ruta} y queda marcado como página actual`, async ({
    page,
  }) => {
    await page.goto(ruta === '/' ? '/tareas' : '/')

    await page.getByRole('link', { name: etiqueta }).click()

    await expect(page).toHaveURL(new RegExp(`${ruta === '/' ? '/' : ruta}$`))
    await expect(page.getByRole('link', { name: etiqueta })).toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('heading', { level: 2, name: etiqueta })).toBeVisible()
  })
}

test('el modo oscuro se conserva al recargar la página, sin parpadeo', async ({ page }) => {
  await page.goto('/')
  await activarModoOscuro(page)

  await page.reload()

  await expect(page.locator('html')).toHaveClass(/\bdark\b/)
  await expect(page.getByRole('switch', { name: 'Cambiar a modo claro' })).toHaveAttribute(
    'aria-checked',
    'true',
  )
})

// Regresión: el historial se volvía a descargar cada vez que se reabría el
// menú de ayuda (reka desmonta su contenido y con él la caché de la modal).
test('el historial de cambios se descarga una sola vez aunque se reabra el menú de ayuda', async ({
  page,
}) => {
  let peticionesHistorial = 0
  await page.route('https://api.github.com/**/releases*', (ruta) => {
    peticionesHistorial += 1
    return ruta.fulfill({ json: [{ tag_name: 'v1.0.0', name: 'v1.0.0', body: '* novedad' }] })
  })
  await page.route('https://api.github.com/**/releases/latest', (ruta) =>
    ruta.fulfill({ json: { tag_name: 'v1.0.0', name: 'v1.0.0', body: '' } }),
  )
  await page.goto('/')

  for (let vuelta = 0; vuelta < 3; vuelta += 1) {
    await page.getByRole('button', { name: 'Ayuda: historial de cambios' }).click()
    await page.getByRole('button', { name: 'Historial de cambios', exact: true }).click()
    const modal = page.getByRole('dialog', { name: 'Historial de cambios', exact: true })
    await expect(modal.getByText('novedad')).toBeVisible()
    await page.keyboard.press('Escape')
    await expect(modal).toBeHidden()
    await page.keyboard.press('Escape')
  }

  expect(peticionesHistorial).toBe(1)
})
