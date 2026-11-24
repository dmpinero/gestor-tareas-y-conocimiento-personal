import { test, expect, type Page } from './base'
import AxeBuilder from '@axe-core/playwright'
import { activarModoOscuro } from './utilidades'

// La página de oportunidades habla con el servicio "automatizador", que abre un
// navegador real contra una herramienta corporativa: en e2e su API se simula
// siempre y nunca se lanza ninguna automatización real.
const CONFIGURACION = {
  valores: {
    perfil: 'Persona Ejemplo',
    cliente: '[CEJ] Cliente Ejemplo S.A.',
    grupo: 'Grupo Ejemplo',
    tipo: 'Tipo Ejemplo',
    segmentacion: 'Segmentación Ejemplo',
    fase: '1 - Fase Ejemplo',
    probabilidad: '50',
    dias_fecha_limite: 7,
    tipo_servicio: 'Servicio Ejemplo',
    lineas_negocio: [{ nombre: 'Línea Ejemplo', porcentaje: '100' }],
    comunidades: [{ nombre: 'Comunidad A', porcentaje: '100' }],
  },
  error: null,
  fecha_limite: '07/02/2026',
  fecha_inicio: '28/02/2026',
  nombre_menu: 'Oportunidades Ejemplo',
}

const EJECUCION_CON_PREGUNTA = {
  id: 'e2e',
  prj: 'PRJ-00001',
  estado: 'en_curso',
  terminada: false,
  pasos: ['Abriendo el navegador', 'Sesión iniciada'],
  pregunta: {
    id: 1,
    tipo: 'guardar',
    mensaje: 'Revisa los valores del formulario. ¿Guardar la oportunidad?',
    detalle: 'Nombre: PRJ-00001 Proyecto de ejemplo',
    opciones: [
      { valor: 'guardar', etiqueta: 'Guardar' },
      { valor: 'no_guardar', etiqueta: 'No guardar' },
    ],
  },
  mensaje_final: null,
  hay_captura: false,
}

async function simularApi(page: Page, ejecucion: object | null = null): Promise<string[]> {
  const respuestas: string[] = []
  // Esta página no necesita el backend: cualquier otra llamada a la API se
  // responde aquí (Playwright usa la última ruta registrada que coincide).
  await page.route('**/api/v1/**', (ruta) =>
    ruta.fulfill({ status: 404, json: { detalle: 'Simulado en e2e' } }),
  )
  await page.route('**/api/v1/alta-oportunidades/configuracion', (ruta) =>
    ruta.fulfill({ json: CONFIGURACION }),
  )
  await page.route('**/api/v1/alta-oportunidades/ejecucion', (ruta) =>
    ejecucion
      ? ruta.fulfill({ json: ejecucion })
      : ruta.fulfill({ status: 404, json: { detalle: 'Sin altas' } }),
  )
  await page.route('**/api/v1/alta-oportunidades/ejecucion/respuesta', async (ruta) => {
    respuestas.push(ruta.request().postData() ?? '')
    await ruta.fulfill({
      json: {
        ...EJECUCION_CON_PREGUNTA,
        estado: 'no_guardada',
        terminada: true,
        pregunta: null,
        mensaje_final: 'No se ha guardado nada.',
      },
    })
  })
  return respuestas
}

async function auditarPagina(page: Page) {
  return new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
}

test('el enlace del alta, dentro de la sección "Oportunidades" del menú, abre la página', async ({
  page,
}) => {
  await simularApi(page)
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Expandir panel de navegación' }).click()

  await page.getByRole('link', { name: 'Oportunidades Ejemplo' }).click()

  await expect(page).toHaveURL(/\/oportunidades\/anes$/)
  await expect(page.getByRole('link', { name: 'Oportunidades Ejemplo' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(page.getByRole('heading', { level: 2, name: 'Oportunidades Ejemplo' })).toBeVisible()
  await expect(page.getByText('[CEJ] Cliente Ejemplo S.A.')).toBeVisible()
})

test('la pregunta final se responde desde la página', async ({ page }) => {
  const respuestas = await simularApi(page, EJECUCION_CON_PREGUNTA)
  await page.goto('/oportunidades/anes')

  await expect(page.getByRole('heading', { name: '¿Guardar la oportunidad?' })).toBeFocused()
  await page.getByRole('button', { name: 'No guardar', exact: true }).click()

  await expect(page.getByText('No se ha guardado nada.')).toBeVisible()
  expect(respuestas).toEqual([JSON.stringify({ id_pregunta: 1, valor: 'no_guardar' })])
})

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`/oportunidades/anes con un error de validación no tiene violaciones de accesibilidad en modo ${modo} (WCAG 2.1 AA)`, async ({
    page,
  }) => {
    await simularApi(page)
    await page.goto('/oportunidades/anes')
    await preparar(page)
    await page.getByLabel('Código del proyecto').fill('PRJ-1')
    await page.getByLabel('Código del proyecto').blur()
    await expect(
      page.getByText('El código debe tener el formato PRJ-XXXXX (5 dígitos).'),
    ).toBeVisible()

    const resultado = await auditarPagina(page)

    expect(resultado.violations).toEqual([])
  })

  test(`/oportunidades/anes con una pregunta pendiente no tiene violaciones de accesibilidad en modo ${modo} (WCAG 2.1 AA)`, async ({
    page,
  }) => {
    await simularApi(page, EJECUCION_CON_PREGUNTA)
    await page.goto('/oportunidades/anes')
    await preparar(page)
    await expect(page.getByRole('button', { name: 'Guardar', exact: true })).toBeVisible()

    const resultado = await auditarPagina(page)

    expect(resultado.violations).toEqual([])
  })
}
