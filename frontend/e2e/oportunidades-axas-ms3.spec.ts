import { test, expect, type Page } from './base'
import AxeBuilder from '@axe-core/playwright'
import { activarModoOscuro } from './utilidades'

// Alta AXAS MS3: como en el alta de ANES, la API del servicio "automatizador"
// se simula siempre y nunca se lanza ninguna automatización real. El catálogo
// de códigos de servicio también se simula aquí para que el test no dependa de
// lo que haya en la base de datos (la página de Ajustes se prueba aparte contra
// el backend real).
const CONFIGURACION = {
  valores: {
    perfil: 'Responsable Ejemplo',
    cliente: '[CEJ] Cliente Ejemplo S.A.',
    grupo: 'Grupo Ejemplo',
    tipo: 'Tipo Ejemplo',
    segmentacion: 'Segmentación Ejemplo',
    fase: '1 - Fase Ejemplo',
    probabilidad: '50',
    dias_fecha_limite: 7,
    tipo_servicio: 'Servicio MS3 Ejemplo',
    lineas_negocio: [{ nombre: 'Línea Ejemplo', porcentaje: '100' }],
    comunidades: [{ nombre: 'Comunidad A', porcentaje: '100' }],
    responsable_operaciones: 'Operaciones Ejemplo',
    responsable_tecnico: 'Técnico Ejemplo',
    area_ms3: 'Área Ejemplo',
  },
  error: null,
  fecha_limite: '07/02/2026',
  fecha_inicio: '28/02/2026',
  nombre_menu: 'AXAS Ejemplo',
}

interface Simulacion {
  altas: unknown[]
  codigosCreados: unknown[]
}

async function simularApi(page: Page): Promise<Simulacion> {
  const simulacion: Simulacion = { altas: [], codigosCreados: [] }
  const codigos = [{ id: 1, nombre: 'AXAS0024' }]
  await page.route('**/api/v1/**', (ruta) =>
    ruta.fulfill({ status: 404, json: { detalle: 'Simulado en e2e' } }),
  )
  await page.route('**/api/v1/codigos-servicio', async (ruta) => {
    if (ruta.request().method() === 'POST') {
      const cuerpo = ruta.request().postDataJSON() as { nombre: string }
      simulacion.codigosCreados.push(cuerpo)
      const creado = { id: codigos.length + 1, nombre: cuerpo.nombre }
      codigos.push(creado)
      await ruta.fulfill({ status: 201, json: creado })
    } else {
      await ruta.fulfill({ json: codigos })
    }
  })
  await page.route('**/api/v1/alta-oportunidades/axas-ms3/configuracion', (ruta) =>
    ruta.fulfill({ json: CONFIGURACION }),
  )
  await page.route('**/api/v1/alta-oportunidades/ejecucion', (ruta) =>
    ruta.fulfill({ status: 404, json: { detalle: 'Sin altas' } }),
  )
  await page.route('**/api/v1/alta-oportunidades/axas-ms3/ejecucion', async (ruta) => {
    simulacion.altas.push(ruta.request().postDataJSON())
    await ruta.fulfill({
      status: 201,
      json: {
        id: 'e2e',
        prj: 'AXAS-MS3-EV25-Portal de clientes',
        estado: 'en_curso',
        terminada: false,
        pasos: ['Abriendo el navegador'],
        pregunta: null,
        mensaje_final: null,
        hay_captura: false,
      },
    })
  })
  return simulacion
}

test('el enlace del alta AXAS MS3, dentro de la sección "Oportunidades", abre su página', async ({
  page,
}) => {
  await simularApi(page)
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Expandir panel de navegación' }).click()

  await page.getByRole('link', { name: 'AXAS Ejemplo' }).click()

  await expect(page).toHaveURL(/\/oportunidades\/axas-ms3$/)
  await expect(page.getByRole('link', { name: 'AXAS Ejemplo' })).toHaveAttribute(
    'aria-current',
    'page',
  )
  await expect(page.getByRole('heading', { level: 2, name: 'AXAS Ejemplo' })).toBeVisible()
  await expect(page.getByText('Área Ejemplo')).toBeVisible()
})

test('crea un código de servicio desde el combobox y lanza el alta con el nombre compuesto', async ({
  page,
}) => {
  const simulacion = await simularApi(page)
  await page.goto('/oportunidades/axas-ms3')

  const combobox = page.getByRole('combobox', { name: 'Código de servicio' })
  await combobox.fill('AXAS0025')
  await page.getByRole('option', { name: 'Crear "AXAS0025"' }).click()
  await expect(combobox).toHaveValue('AXAS0025')
  await page.getByLabel('Descripción').fill('Portal de clientes')
  await page.getByLabel('Duración (meses)').fill('6')
  await page.getByLabel('Importe total previsto (EUR)').fill('1000')
  await page.getByLabel('Coste total previsto (EUR)').fill('800')
  await expect(page.getByText('AXAS-MS3-EV25-Portal de clientes')).toBeVisible()

  await page.getByRole('button', { name: 'Crear oportunidad' }).click()

  await expect(page.getByText('Avance del alta de AXAS-MS3-EV25-Portal de clientes')).toBeVisible()
  expect(simulacion.codigosCreados).toEqual([{ nombre: 'AXAS0025' }])
  expect(simulacion.altas).toEqual([
    {
      codigo_servicio: 'AXAS0025',
      descripcion: 'Portal de clientes',
      duracion: 6,
      importe: 1000,
      coste: 800,
    },
  ])
})

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`/oportunidades/axas-ms3 con el combobox abierto y errores no tiene violaciones de accesibilidad en modo ${modo} (WCAG 2.1 AA)`, async ({
    page,
  }) => {
    await simularApi(page)
    await page.goto('/oportunidades/axas-ms3')
    await preparar(page)
    await page.getByRole('button', { name: 'Crear oportunidad' }).click()
    await expect(page.getByText('La descripción es obligatoria.')).toBeVisible()
    await page.getByRole('combobox', { name: 'Código de servicio' }).fill('AXAS')
    await expect(page.getByRole('option', { name: 'AXAS0024' })).toBeVisible()

    const resultado = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .exclude('.vue-devtools__anchor-btn')
      .analyze()

    expect(resultado.violations).toEqual([])
  })
}

test('en Ajustes se añade, renombra y elimina un código de servicio', async ({ page }) => {
  const codigo = `E2E${Date.now().toString().slice(-6)}`
  await page.goto('/ajustes')
  await page.getByRole('link', { name: 'Códigos de servicio' }).click()
  await expect(page.getByRole('heading', { level: 2, name: 'Códigos de servicio' })).toBeVisible()

  await page.getByLabel('Código de servicio', { exact: true }).fill(codigo)
  await page.getByRole('button', { name: 'Añadir código' }).click()
  const lista = page.getByRole('list', { name: 'Códigos de servicio' })
  await expect(lista.getByText(codigo, { exact: true })).toBeVisible()

  await page.getByRole('button', { name: `Renombrar código de servicio ${codigo}` }).click()
  await page.getByLabel(`Nuevo nombre del código de servicio ${codigo}`).fill(`${codigo}X`)
  await page.getByRole('button', { name: 'Guardar' }).click()
  await expect(lista.getByText(`${codigo}X`, { exact: true })).toBeVisible()

  await page.getByRole('button', { name: `Eliminar código de servicio ${codigo}X` }).click()
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: /Eliminar/ })
    .click()
  await expect(lista.getByText(`${codigo}X`, { exact: true })).toHaveCount(0)
})
