import { expect, type Page } from '@playwright/test'

/** Rutas de primer nivel de la barra lateral, con la etiqueta de su enlace y el
 * título de su página (si no es la etiqueta). */
export const SECCIONES = [
  { ruta: '/', etiqueta: 'Inicio' },
  { ruta: '/tareas', etiqueta: 'Mi trabajo', titulo: 'Tareas' },
  { ruta: '/conocimiento', etiqueta: 'Conocimiento' },
  { ruta: '/ajustes', etiqueta: 'Ajustes' },
] as const

/**
 * Pulsa el conmutador de tema y espera a que el documento quede en modo
 * oscuro, para no auditar ni capturar la página a mitad del cambio.
 */
export async function activarModoOscuro(page: Page): Promise<void> {
  await page.getByRole('switch', { name: 'Cambiar a modo oscuro' }).click()
  await expect(page.locator('html')).toHaveClass(/\bdark\b/)
}
