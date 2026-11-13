import { test, expect, type APIRequestContext, type Locator, type Page } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
import { activarModoOscuro } from './utilidades'

// Cada test crea sus propios workflows con nombres únicos: no comparten estado.

function pasosDe(page: Page, workflow: string) {
  return page.getByRole('list', { name: `Pasos de ${workflow}` }).locator('[data-texto-paso]')
}

async function crearWorkflow(page: Page, workflow: string, pasos: string[]): Promise<void> {
  await page.goto('/ajustes')
  await page.getByRole('link', { name: 'Workflows' }).click()
  await expect(page).toHaveURL(/\/ajustes\/workflows$/)
  await page.getByLabel('Nombre del workflow').fill(workflow)
  await page.getByRole('button', { name: 'Añadir workflow' }).click()
  await expect(page.getByRole('heading', { name: workflow })).toBeVisible()
  for (const paso of pasos) {
    await page.getByRole('textbox', { name: `Nuevo paso de ${workflow}` }).fill(paso)
    await page.getByRole('button', { name: `Añadir paso a ${workflow}` }).click()
    await expect(pasosDe(page, workflow).filter({ hasText: paso })).toHaveCount(1)
  }
}

/** Crea por la API un workflow con un paso que ya tiene comentarios. */
async function crearWorkflowConComentarios(
  request: APIRequestContext,
  workflow: string,
  paso: string,
  comentarios: string[],
): Promise<void> {
  const creado = await request.post('/api/v1/workflows', { data: { nombre: workflow } })
  expect(creado.status()).toBe(201)
  const { id } = (await creado.json()) as { id: number }
  const conPaso = await request.post(`/api/v1/workflows/${id}/pasos`, { data: { nombre: paso } })
  expect(conPaso.status()).toBe(201)
  const { pasos } = (await conPaso.json()) as { pasos: { id: number }[] }
  for (const texto of comentarios) {
    const comentario = await request.post(
      `/api/v1/workflows/${id}/pasos/${pasos[0]!.id}/comentarios`,
      { data: { texto } },
    )
    expect(comentario.status()).toBe(201)
  }
}

/** Botón que abre los comentarios de un paso; su nombre incluye el número si hay. */
function botonComentariosPaso(page: Page, workflow: string, paso: string, numero = 0) {
  const base = `Comentarios del paso ${paso} de ${workflow}`
  return page.getByRole('button', { name: numero > 0 ? `${base}: ${numero}` : base, exact: true })
}

/** Comentario concreto del historial (los de un día van en una lista anidada). */
function comentario(panel: Locator, texto: string) {
  return panel.locator('ol ol > li').filter({ hasText: texto })
}

/** Edita un comentario de `ComentariosTarea` confirmando el cambio. */
async function editarComentario(
  panel: Locator,
  contexto: string,
  anterior: string,
  nuevo: string,
): Promise<void> {
  await comentario(panel, anterior)
    .getByRole('button', { name: /^Editar comentario de las / })
    .click()
  await panel.getByRole('textbox', { name: `Nuevo texto del comentario ${contexto}` }).fill(nuevo)
  await panel
    .getByRole('form', { name: `Editar comentario ${contexto}` })
    .getByRole('button', { name: 'Guardar' })
    .click()
  await panel
    .getByRole('group', { name: `¿Guardar los cambios del comentario ${contexto}?` })
    .getByRole('button', { name: 'Guardar' })
    .click()
  await expect(comentario(panel, nuevo)).toBeVisible()
}

async function esperarAnimaciones(elemento: Locator): Promise<void> {
  // Las animaciones infinitas (indicadores de carga) no terminan nunca.
  await elemento.evaluate((nodo) =>
    Promise.all(
      nodo
        .getAnimations({ subtree: true })
        .filter((animacion) => animacion.effect?.getTiming().iterations !== Infinity)
        .map((animacion) => animacion.finished),
    ),
  )
}

async function sinViolaciones(page: Page): Promise<void> {
  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
}

test('la ruta antigua del workflow lleva a la página de workflows', async ({ page }) => {
  await page.goto('/ajustes/workflow-oportunidades')
  await expect(page).toHaveURL(/\/ajustes\/workflows$/)
  await expect(page.getByRole('heading', { name: 'Workflows', exact: true })).toBeVisible()
})

test('gestiona varios workflows y sus pasos desde Ajustes', async ({ page }) => {
  const marca = Date.now()
  const workflow = `Ventas ${marca}`
  await crearWorkflow(page, workflow, ['Contactar', 'Proponer', 'Cerrar'])
  await expect(pasosDe(page, workflow)).toHaveText(['1. Contactar', '2. Proponer', '3. Cerrar'])

  // Obligatorio.
  await page.getByRole('button', { name: `Añadir paso a ${workflow}` }).click()
  await expect(page.getByText('El nombre del paso es obligatorio.')).toBeVisible()

  // Reordenar con los botones accesibles y con drag & drop.
  await page.getByRole('button', { name: `Bajar paso Contactar de ${workflow}` }).click()
  await expect(pasosDe(page, workflow)).toHaveText(['1. Proponer', '2. Contactar', '3. Cerrar'])
  await expect(page.locator('[aria-live="polite"]')).toContainText(
    'Contactar movido a la posición 2',
  )
  const filas = page.getByRole('list', { name: `Pasos de ${workflow}` }).locator('li[data-paso]')
  await filas.filter({ hasText: 'Cerrar' }).dragTo(filas.filter({ hasText: 'Proponer' }))
  await expect(pasosDe(page, workflow)).toHaveText(['1. Cerrar', '2. Proponer', '3. Contactar'])
  await page.screenshot({ path: 'e2e/capturas/workflow-01-pasos.png' })

  // Renombrar y eliminar un paso (los siguientes se renumeran).
  await page.getByRole('button', { name: `Renombrar paso Proponer de ${workflow}` }).click()
  await page.getByLabel(`Nuevo nombre del paso Proponer de ${workflow}`).fill('Enviar propuesta')
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.getByRole('button', { name: `Eliminar paso Cerrar de ${workflow}` }).click()
  await page
    .getByRole('alertdialog', { name: '¿Eliminar el paso Cerrar?' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(pasosDe(page, workflow)).toHaveText(['1. Enviar propuesta', '2. Contactar'])

  // Renombrar el workflow; se guarda al recargar.
  await page.getByRole('button', { name: `Renombrar workflow ${workflow}` }).click()
  await page.getByLabel(`Nuevo nombre del workflow ${workflow}`).fill(`${workflow} B2B`)
  await page.getByRole('button', { name: 'Guardar' }).click()
  await page.reload()
  await expect(pasosDe(page, `${workflow} B2B`)).toHaveText(['1. Enviar propuesta', '2. Contactar'])
  await sinViolaciones(page)

  // Eliminar el workflow avisa de que las tareas conservan sus subtareas.
  await page.getByRole('button', { name: `Eliminar workflow ${workflow} B2B` }).click()
  const confirmar = page.getByRole('alertdialog', {
    name: `¿Eliminar el workflow ${workflow} B2B?`,
  })
  await expect(confirmar).toContainText('conservarán sus subtareas')
  await confirmar.getByRole('button', { name: 'Eliminar' }).click()
  await expect(page.getByRole('heading', { name: `${workflow} B2B` })).toHaveCount(0)
})

test('el workflow de la tarea añade sus pasos como subtareas al crearla y al cambiarlo', async ({
  page,
}) => {
  const marca = Date.now()
  const primero = `Alta ${marca}`
  const segundo = `Cierre ${marca}`
  const tarea = `Tarea con workflow ${marca}`
  await crearWorkflow(page, primero, ['Llamar', 'Visitar'])
  await crearWorkflow(page, segundo, ['Facturar'])

  // Alta con el primer workflow: sus pasos llegan como subtareas.
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  await ventana.getByPlaceholder('Nombre').fill(tarea)
  await ventana.getByPlaceholder('Descripción').fill('Con workflow')
  await ventana.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: primero })
  await ventana.getByRole('button', { name: 'Guardar' }).click()
  await expect(ventana).toBeHidden()

  const abrirDetalle = async () => {
    await page.getByRole('button', { name: `Ver detalle de la tarea ${tarea}` }).click()
    return page.getByRole('dialog', { name: tarea })
  }
  let detalle = await abrirDetalle()
  await expect(detalle.getByTestId('campos-tarea')).toContainText(primero)
  for (const paso of ['Llamar', 'Visitar']) {
    await expect(
      detalle.getByRole('button', { name: `Marcar como resuelta la subtarea ${paso}` }),
    ).toBeVisible()
  }
  await page.keyboard.press('Escape')

  // Editar y elegir otro workflow: añade sus pasos y conserva los anteriores.
  await page.getByRole('button', { name: `Editar tarea ${tarea}` }).click()
  const edicion = page.getByRole('dialog', { name: 'Editar tarea' })
  await expect(edicion.getByRole('combobox', { name: 'Workflow' })).toHaveValue(/\d+/)
  await edicion.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: segundo })
  await edicion.getByRole('button', { name: 'Guardar' }).click()
  await expect(edicion).toBeHidden()

  detalle = await abrirDetalle()
  for (const paso of ['Llamar', 'Visitar', 'Facturar']) {
    await expect(
      detalle.getByRole('button', { name: `Marcar como resuelta la subtarea ${paso}` }),
    ).toBeVisible()
  }
  await page.screenshot({ path: 'e2e/capturas/workflow-02-pasos-tarea.png' })
})

test('al elegir el tipo Oportunidad en el alta se preselecciona "Workflow Oportunidades"', async ({
  page,
}) => {
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  const workflow = ventana.getByRole('combobox', { name: 'Workflow' })
  await expect(workflow).toHaveValue('')
  await ventana.getByLabel('Tipo de tarea').selectOption({ label: 'Oportunidad' })
  await expect(workflow.locator('option:checked')).toHaveText('Workflow Oportunidades')
})

// Regresión (accesibilidad): al mover con el teclado, el foco se perdía en el
// <body> porque el botón pulsado se desactiva mientras se guarda.
test('al reordenar con el teclado el foco se queda en el paso movido', async ({ page }) => {
  const workflow = `Teclado ${Date.now()}`
  await crearWorkflow(page, workflow, ['Uno', 'Dos', 'Tres'])

  await page.getByRole('button', { name: `Bajar paso Uno de ${workflow}` }).focus()
  await page.keyboard.press('Enter')
  await expect(pasosDe(page, workflow)).toHaveText(['1. Dos', '2. Uno', '3. Tres'])
  await expect(page.getByRole('button', { name: `Bajar paso Uno de ${workflow}` })).toBeFocused()

  await page.keyboard.press('Enter')
  await expect(pasosDe(page, workflow)).toHaveText(['1. Dos', '2. Tres', '3. Uno'])
  // Ya está al final: el foco pasa a su botón "Subir".
  await expect(page.getByRole('button', { name: `Subir paso Uno de ${workflow}` })).toBeFocused()
})

test('cada paso tiene su historial de comentarios en Ajustes', async ({ page }) => {
  const workflow = `Comentarios ${Date.now()}`
  const contexto = `del paso Revisar de ${workflow}`
  await crearWorkflow(page, workflow, ['Revisar'])
  await botonComentariosPaso(page, workflow, 'Revisar').click()
  const panel = page.getByTestId('comentarios-paso')
  await expect(panel).toContainText('Todavía no hay comentarios.')

  // Añadir: el contador del paso se actualiza.
  const campo = panel.getByRole('textbox', { name: `Escribe un comentario ${contexto}` })
  const enviar = panel.getByRole('button', { name: `Enviar comentario ${contexto}` })
  await campo.fill('Primera nota')
  await enviar.click()
  await expect(comentario(panel, 'Primera nota')).toBeVisible()
  await expect(botonComentariosPaso(page, workflow, 'Revisar', 1)).toBeVisible()
  await campo.fill('Segunda nota')
  await enviar.click()
  await expect(comentario(panel, 'Segunda nota')).toBeVisible()
  await expect(botonComentariosPaso(page, workflow, 'Revisar', 2)).toBeVisible()

  // Editar con confirmación: queda la marca "(editado)".
  await editarComentario(panel, contexto, 'Primera nota', 'Primera nota corregida')
  await expect(
    comentario(panel, 'Primera nota corregida').getByTestId('marca-editado'),
  ).toBeVisible()

  // Borrar con confirmación.
  await comentario(panel, 'Segunda nota')
    .getByRole('button', { name: /^Eliminar comentario de las / })
    .click()
  await panel
    .getByRole('group', { name: `¿Eliminar el comentario ${contexto}?` })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(comentario(panel, 'Segunda nota')).toHaveCount(0)
  await expect(botonComentariosPaso(page, workflow, 'Revisar', 1)).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/workflow-03-comentarios-paso.png' })

  // Se guarda: tras recargar siguen el contador y el comentario editado.
  await page.reload()
  await botonComentariosPaso(page, workflow, 'Revisar', 1).click()
  await expect(comentario(panel, 'Primera nota corregida')).toBeVisible()
  await expect(comentario(panel, 'Segunda nota')).toHaveCount(0)
})

test('los comentarios del paso se copian a las subtareas y luego son independientes', async ({
  page,
  request,
}) => {
  const marca = Date.now()
  const workflow = `Copia ${marca}`
  const conAlta = `Alta con comentarios ${marca}`
  const conEdicion = `Edición con comentarios ${marca}`
  await crearWorkflowConComentarios(request, workflow, 'Llamar', ['Guion de llamada', 'Pedir cita'])
  const sinWorkflow = await request.post('/api/v1/tareas', {
    data: {
      nombre: conEdicion,
      descripcion: 'Sin workflow',
      fecha_creacion: '2026-01-01T09:00:00',
    },
  })
  expect(sinWorkflow.status()).toBe(201)

  // Alta con el workflow: la subtarea nace con una copia de los comentarios, en orden.
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  await ventana.getByPlaceholder('Nombre').fill(conAlta)
  await ventana.getByPlaceholder('Descripción').fill('Con workflow')
  await ventana.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: workflow })
  await ventana.getByRole('button', { name: 'Guardar' }).click()
  await expect(ventana).toBeHidden()

  const abrirComentariosSubtarea = async (tarea: string) => {
    await page.getByRole('button', { name: `Ver detalle de la tarea ${tarea}` }).click()
    const detalle = page.getByRole('dialog', { name: tarea })
    await detalle.getByRole('button', { name: 'Comentarios de la subtarea Llamar: 2' }).click()
    const panel = detalle.getByTestId('comentarios-subtarea')
    await expect(panel.locator('ol ol > li')).toHaveCount(2)
    return panel
  }
  let panel = await abrirComentariosSubtarea(conAlta)
  await expect(panel.locator('ol ol > li p')).toHaveText(['Guion de llamada', 'Pedir cita'])
  // La copia es nueva: no está editada.
  await expect(panel.getByTestId('marca-editado')).toHaveCount(0)

  // Editar la copia en la subtarea no cambia el paso.
  await editarComentario(panel, 'de la subtarea Llamar', 'Guion de llamada', 'Guion adaptado')
  await page.keyboard.press('Escape')

  // Elegir el workflow al editar otra tarea también copia los comentarios.
  await page.getByRole('button', { name: `Editar tarea ${conEdicion}` }).click()
  const edicion = page.getByRole('dialog', { name: 'Editar tarea' })
  await edicion.getByRole('combobox', { name: 'Workflow' }).selectOption({ label: workflow })
  await edicion.getByRole('button', { name: 'Guardar' }).click()
  await expect(edicion).toBeHidden()
  panel = await abrirComentariosSubtarea(conEdicion)
  await expect(panel.locator('ol ol > li p')).toHaveText(['Guion de llamada', 'Pedir cita'])
  await page.screenshot({ path: 'e2e/capturas/workflow-04-comentarios-copiados.png' })

  // En Ajustes el paso conserva su comentario original.
  await page.goto('/ajustes/workflows')
  await botonComentariosPaso(page, workflow, 'Llamar', 2).click()
  const panelPaso = page.getByTestId('comentarios-paso')
  await expect(panelPaso.locator('ol ol > li p')).toHaveText(['Guion de llamada', 'Pedir cita'])
  await expect(panelPaso.getByTestId('marca-editado')).toHaveCount(0)

  // Editar el comentario del paso no cambia las copias ya hechas.
  await editarComentario(
    panelPaso,
    `del paso Llamar de ${workflow}`,
    'Guion de llamada',
    'Guion revisado',
  )
  await page.goto('/tareas')
  panel = await abrirComentariosSubtarea(conEdicion)
  await expect(panel.locator('ol ol > li p')).toHaveText(['Guion de llamada', 'Pedir cita'])
  await page.keyboard.press('Escape')
  panel = await abrirComentariosSubtarea(conAlta)
  await expect(panel.locator('ol ol > li p')).toHaveText(['Guion adaptado', 'Pedir cita'])
})

const MODOS = [
  { modo: 'claro', preparar: async (_page: Page) => {} },
  { modo: 'oscuro', preparar: activarModoOscuro },
] as const

for (const { modo, preparar } of MODOS) {
  test(`los comentarios abiertos de un paso no tienen violaciones de accesibilidad en modo ${modo} (WCAG 2.1 AA)`, async ({
    page,
    request,
  }) => {
    const workflow = `Accesible ${modo} ${Date.now()}`
    await crearWorkflowConComentarios(request, workflow, 'Auditar', ['Primero'])
    await page.goto('/ajustes/workflows')
    await preparar(page)
    await botonComentariosPaso(page, workflow, 'Auditar', 1).click()
    const panel = page.getByTestId('comentarios-paso')
    await expect(comentario(panel, 'Primero')).toBeVisible()
    await esperarAnimaciones(panel)
    await sinViolaciones(page)
  })
}
