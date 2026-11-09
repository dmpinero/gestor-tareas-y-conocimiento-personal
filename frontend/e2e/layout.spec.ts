import { test, expect } from '@playwright/test'
import { activarModoOscuro, SECCIONES } from './utilidades'

test('el panel de navegación colapsa y expande, y resalta la sección activa', async ({ page }) => {
  await page.goto('/')
  await page.screenshot({ path: 'e2e/capturas/layout-01-sidebar-expandido.png' })

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

  await botonColapsar.click()
  await expect(botonExpandir).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/layout-02-sidebar-colapsado.png' })

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
