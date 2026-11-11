import { test, expect } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'

test('crea una tarea desde la ventana modal y aparece en el listado', async ({ page }) => {
  // Nombre único: la base de datos de la pila local no se vacía entre ejecuciones.
  const nombre = `Tarea e2e ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()

  const panel = page.getByRole('dialog')
  await expect(panel).toBeVisible()
  await expect(panel.getByRole('heading', { name: 'Crear tarea' })).toBeVisible()
  await page.screenshot({ path: 'e2e/capturas/tareas-01-panel-crear.png' })

  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Prioridad').fill('2')
  await panel.getByPlaceholder('Descripción').fill('Descripción creada desde el test e2e')
  await panel.getByRole('button', { name: 'Guardar' }).click()

  await expect(panel).toBeHidden()
  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toBeVisible()
  await expect(fila).toContainText('2')
  await expect(fila).toContainText('Descripción creada desde el test e2e')
  await page.screenshot({ path: 'e2e/capturas/tareas-02-listado.png' })
})

test('una tarea sin prioridad se muestra con un guion', async ({ page }) => {
  const nombre = `Tarea sin prioridad ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()

  const panel = page.getByRole('dialog')
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Sin prioridad')
  await panel.getByRole('button', { name: 'Guardar' }).click()

  await expect(panel).toBeHidden()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('—')
})

test('el listado sigue siendo accesible con nombres y descripciones de longitud máxima', async ({
  page,
}) => {
  // Regresión: con `whitespace-nowrap` un nombre largo desbordaba la tabla en
  // horizontal y axe marcaba `scrollable-region-focusable`.
  const marca = `${Date.now()}`
  const conEspacios = `${marca} ${'palabra '.repeat(30)}`.slice(0, 200)
  const sinEspacios = `${marca}${'x'.repeat(200)}`.slice(0, 200)

  await page.goto('/tareas')
  for (const nombre of [conEspacios, sinEspacios]) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByPlaceholder('Nombre').fill(nombre)
    await panel.getByPlaceholder('Descripción').fill('d'.repeat(500))
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])
})

test('la fecha de creación se rellena con la actual y se puede editar una tarea', async ({
  page,
}) => {
  const nombre = `Tarea a editar ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog')
  await expect(panel.locator('#fecha-creacion')).toHaveValue(
    /^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}$/,
  )
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Antes de editar')
  await panel.locator('#fecha-creacion').fill('09/11/2026 08:30:15')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('09/11/2026 08:30:15')

  await page.getByRole('button', { name: `Editar tarea ${nombre}` }).click()
  await expect(panel.getByRole('heading', { name: 'Editar tarea' })).toBeVisible()
  await expect(panel.getByPlaceholder('Nombre')).toHaveValue(nombre)
  await expect(panel.locator('#fecha-creacion')).toHaveValue('09/11/2026 08:30:15')
  await page.screenshot({ path: 'e2e/capturas/tareas-03-panel-editar.png' })

  await panel.getByPlaceholder('Descripción').fill('Después de editar')
  await panel.getByPlaceholder('Prioridad').fill('1')
  await panel.locator('#fecha-creacion').fill('31/12/2026 23:59:59')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toContainText('Después de editar')
  await expect(fila).toContainText('31/12/2026 23:59:59')
  await page.reload()
  await expect(page.locator('tr', { hasText: nombre })).toContainText('Después de editar')
})

test('ordena la tabla por una columna y exporta el listado a Excel y PDF', async ({ page }) => {
  const marca = `${Date.now()}`
  const nombres = [`zz ${marca}`, `aa ${marca}`]

  await page.goto('/tareas')
  for (const nombre of nombres) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    const panel = page.getByRole('dialog')
    await panel.getByPlaceholder('Nombre').fill(nombre)
    await panel.getByPlaceholder('Descripción').fill('Para ordenar y exportar')
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const cabeceraNombre = page.getByRole('columnheader', { name: 'Nombre' })
  const filasDeLaPrueba = page.locator('tbody tr', { hasText: marca })

  await cabeceraNombre.getByRole('button', { name: 'Nombre' }).click()
  await expect(cabeceraNombre).toHaveAttribute('aria-sort', 'ascending')
  await expect(filasDeLaPrueba.first()).toContainText(`aa ${marca}`)

  await cabeceraNombre.getByRole('button', { name: 'Nombre' }).click()
  await expect(cabeceraNombre).toHaveAttribute('aria-sort', 'descending')
  await expect(filasDeLaPrueba.first()).toContainText(`zz ${marca}`)
  await page.screenshot({ path: 'e2e/capturas/tareas-04-ordenada.png' })

  const [descargaExcel] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Exportar a Excel' }).click(),
  ])
  expect(descargaExcel.suggestedFilename()).toMatch(/^Tareas_\d{8}_\d{6}\.xlsx$/)

  const [descargaPdf] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: 'Exportar a PDF' }).click(),
  ])
  expect(descargaPdf.suggestedFilename()).toMatch(/^Tareas_\d{8}_\d{6}\.pdf$/)
})

test('asigna etiquetas y personas creadas al vuelo y una fecha de vencimiento con el calendario', async ({
  page,
}) => {
  const marca = `${Date.now()}`
  const nombre = `Tarea con etiquetas ${marca}`
  const etiqueta = `etiqueta-${marca}`
  const persona = `Persona ${marca}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  // Por nombre: el calendario también es un `dialog` (popover).
  const panel = page.getByRole('dialog', { name: /^(Crear|Editar) tarea$/ })
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Con etiquetas, personas y vencimiento')
  await panel.locator('#fecha-creacion').fill('09/11/2026 08:00:00')

  const campoEtiquetas = panel.getByRole('combobox', { name: 'Etiquetas' })
  await campoEtiquetas.fill(etiqueta)
  await panel.getByRole('option', { name: `Crear etiqueta "${etiqueta}"` }).click()
  const campoAsignados = panel.getByRole('combobox', { name: 'Asignado a' })
  await campoAsignados.fill(persona)
  await campoAsignados.press('Enter')
  await expect(panel.getByRole('button', { name: `Quitar ${etiqueta}` })).toBeVisible()
  await expect(panel.getByRole('button', { name: `Quitar ${persona}` })).toBeVisible()

  // El vencimiento se elige con el calendario, en el mes siguiente. El día 15
  // aparece una sola vez en la cuadrícula (los días de otros meses quedan en los
  // extremos), así que no hay ambigüedad.
  await panel.getByRole('button', { name: 'Abrir calendario de Fecha de vencimiento' }).click()
  await page.getByRole('button', { name: 'Mes siguiente' }).click()
  await page.screenshot({ path: 'e2e/capturas/tareas-05-calendario.png' })
  await page.getByRole('gridcell').getByText('15', { exact: true }).click()
  await page.getByRole('button', { name: 'Aceptar' }).click()
  await expect(panel.locator('#fecha-vencimiento')).toHaveValue(
    /^15\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2}$/,
  )

  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toContainText(etiqueta)
  await expect(fila).toContainText(persona)
  await expect(fila).toContainText('09/11/2026 08:00:00')
  await expect(fila).toContainText(/15\/\d{2}\/\d{4}/)

  // La etiqueta creada queda en el catálogo y se sugiere en otra tarea.
  await page.getByRole('button', { name: `Editar tarea ${nombre}` }).click()
  await expect(panel.getByRole('button', { name: `Quitar ${etiqueta}` })).toBeVisible()
  await panel.getByRole('button', { name: `Quitar ${persona}` }).click()
  await panel.getByRole('button', { name: 'Borrar fecha' }).click()
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()
  await expect(fila).not.toContainText(persona)

  await page.getByRole('button', { name: 'Crear tarea' }).click()
  await panel.getByRole('combobox', { name: 'Etiquetas' }).fill(etiqueta.toUpperCase())
  await expect(panel.getByRole('option', { name: etiqueta, exact: true })).toBeVisible()
})

test('filtra la tabla por texto, prioridad y fecha de creación, y limpia los filtros', async ({
  page,
}) => {
  const marca = `${Date.now()}`
  const tareas = [
    { nombre: `Revisión ${marca}`, prioridad: '1', fecha: '05/01/2026 10:00:00' },
    { nombre: `Compra ${marca}`, prioridad: '', fecha: '20/02/2026 10:00:00' },
  ]

  await page.goto('/tareas')
  const panel = page.getByRole('dialog', { name: /^(Crear|Editar) tarea$/ })
  for (const tarea of tareas) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    await panel.getByPlaceholder('Nombre').fill(tarea.nombre)
    await panel.getByPlaceholder('Prioridad').fill(tarea.prioridad)
    await panel.getByPlaceholder('Descripción').fill('Para filtrar')
    await panel.locator('#fecha-creacion').fill(tarea.fecha)
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const filas = page.locator('tbody tr', { hasText: marca })
  await expect(filas).toHaveCount(2)

  // Texto sin acentos ni mayúsculas.
  await page.locator('#filtro-buscar').fill(`revision ${marca}`)
  await expect(filas).toHaveCount(1)
  await expect(filas.first()).toContainText(`Revisión ${marca}`)
  await page.screenshot({ path: 'e2e/capturas/tareas-06-filtros.png' })
  await page.locator('#filtro-buscar').fill(marca)
  await expect(filas).toHaveCount(2)

  // Prioridad: se desmarca "Sin prioridad".
  await page.getByRole('button', { name: 'Filtrar por prioridad' }).click()
  await page.getByRole('checkbox', { name: 'Sin prioridad' }).click()
  await page.keyboard.press('Escape')
  await expect(filas).toHaveCount(1)
  await expect(filas.first()).toContainText(`Revisión ${marca}`)

  await page.getByRole('button', { name: 'Limpiar filtros' }).click()
  await page.locator('#filtro-buscar').fill(marca)
  await expect(filas).toHaveCount(2)

  // Fecha de creación: solo febrero de 2026.
  await page.locator('#filtro-creacion-desde').fill('2026-02-01')
  await page.locator('#filtro-creacion-hasta').fill('2026-02-28')
  await expect(filas).toHaveCount(1)
  await expect(filas.first()).toContainText(`Compra ${marca}`)

  // Sin coincidencias.
  await page.locator('#filtro-buscar').fill(`no-existe-${marca}`)
  await expect(page.getByText('Ninguna tarea coincide con los filtros.')).toBeVisible()

  await page.getByRole('button', { name: 'Limpiar filtros' }).click()
  await expect(page.locator('#filtro-buscar')).toHaveValue('')
  await expect(page.locator('#filtro-creacion-desde')).toHaveValue('')
})

test('crea una oportunidad, muestra su tipo en la tabla y todos sus campos en el detalle', async ({
  page,
}) => {
  const marca = `${Date.now()}`
  const nombre = `Oportunidad ${marca}`
  // Prefijo "OP-" para que el código no aparezca dentro del nombre (que lleva la marca).
  const codigo = `OP-${marca.slice(-7)}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog', { name: /^(Crear|Editar) tarea$/ })
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Tarea de tipo oportunidad')
  await panel.getByLabel('Tipo de tarea').selectOption({ label: 'Oportunidad' })
  await panel.getByLabel('Código de la oportunidad').fill(codigo)
  await panel.getByLabel('Descripción de la oportunidad').fill('Cliente interesado')
  await panel.getByLabel('Observaciones').fill('Primera línea\nSegunda línea')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  // En la tabla solo se ve el tipo, no los campos de la oportunidad.
  const fila = page.locator('tr', { hasText: nombre })
  await expect(fila).toContainText('Oportunidad')
  await expect(fila).not.toContainText(codigo)
  await expect(fila).not.toContainText('Cliente interesado')

  // El detalle muestra todos los campos en una modal del 90 % del viewport.
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  await expect(detalle).toBeVisible()
  await expect(detalle).toContainText('Tarea de tipo oportunidad')
  await expect(detalle).toContainText(codigo)
  await expect(detalle).toContainText('Cliente interesado')
  await expect(detalle).toContainText('Segunda línea')
  // Se mide al terminar la animación de entrada (arranca al 95 % del tamaño).
  await detalle.evaluate((elemento) =>
    Promise.all(elemento.getAnimations().map((animacion) => animacion.finished)),
  )
  const caja = await detalle.boundingBox()
  const ventana = page.viewportSize()!
  expect(caja!.width).toBeCloseTo(ventana.width * 0.9, -1)
  expect(caja!.height).toBeCloseTo(ventana.height * 0.9, -1)
  await page.screenshot({ path: 'e2e/capturas/tareas-07-detalle.png' })
  await detalle.getByRole('button', { name: 'Cerrar' }).click()
  await expect(detalle).toBeHidden()

  // Al quitar el tipo, la tarea deja de ser una oportunidad.
  await page.getByRole('button', { name: `Editar tarea ${nombre}` }).click()
  await expect(panel.getByLabel('Código de la oportunidad')).toHaveValue(codigo)
  await panel.getByLabel('Tipo de tarea').selectOption({ label: 'Sin tipo' })
  await expect(panel.getByLabel('Código de la oportunidad')).toBeHidden()
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  await expect(detalle).not.toContainText(codigo)
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()
})

// Regresión: en pantallas bajas el formulario no cabía y no se notaba que se
// podía desplazar ("Guardar" quedaba fuera de la vista al abrir el panel).
test.describe('panel de tarea en una pantalla baja', () => {
  test.use({ viewport: { width: 1280, height: 600 } })

  test('tiene scroll vertical propio y los botones siempre visibles', async ({ page }) => {
    await page.goto('/tareas')
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    const panel = page.getByRole('dialog', { name: 'Crear tarea' })
    await panel.getByLabel('Tipo de tarea').selectOption({ label: 'Oportunidad' })

    // Los botones se ven sin desplazar nada.
    const guardar = panel.getByRole('button', { name: 'Guardar' })
    await expect(guardar).toBeInViewport()
    await expect(panel.getByRole('button', { name: 'Cancelar' })).toBeInViewport()

    // El cuerpo del formulario tiene su propio scroll vertical...
    const cuerpo = panel.getByTestId('cuerpo-formulario-tarea')
    const { desborda, overflowY } = await cuerpo.evaluate((el) => ({
      desborda: el.scrollHeight > el.clientHeight,
      overflowY: getComputedStyle(el).overflowY,
    }))
    expect(desborda).toBe(true)
    expect(overflowY).toBe('scroll')

    // ...y con la rueda del ratón se llega hasta el último campo. Se espera a que
    // acabe la animación de entrada del panel (en CI la rueda llegaba antes).
    await panel.evaluate((elemento) =>
      Promise.all(elemento.getAnimations().map((animacion) => animacion.finished)),
    )
    const caja = await cuerpo.boundingBox()
    await page.mouse.move(caja!.x + caja!.width / 2, caja!.y + caja!.height / 2)
    const observaciones = panel.getByLabel('Observaciones')
    await expect(async () => {
      await page.mouse.wheel(0, 1000)
      await expect(observaciones).toBeInViewport({ timeout: 500 })
    }).toPass()
    await expect(guardar).toBeInViewport()
  })
})

test('muestra una cuenta atrás hasta el vencimiento que avanza sola, y "Vencida" en rojo', async ({
  page,
}) => {
  const marca = `${Date.now()}`
  // Vencimientos relativos a ahora para cubrir los colores de 24 y 48 horas.
  const dentroDeHoras = (horas: number) => {
    const fecha = new Date(Date.now() + horas * 3600 * 1000)
    const dos = (n: number) => String(n).padStart(2, '0')
    return `${dos(fecha.getDate())}/${dos(fecha.getMonth() + 1)}/${fecha.getFullYear()} ${dos(fecha.getHours())}:${dos(fecha.getMinutes())}:${dos(fecha.getSeconds())}`
  }
  const tareas = [
    { nombre: `Futura ${marca}`, vencimiento: '31/12/2099 23:59:59' },
    { nombre: `Pasada ${marca}`, vencimiento: '02/01/2026 10:00:00' },
    { nombre: `En 30 h ${marca}`, vencimiento: dentroDeHoras(30) },
    { nombre: `En 5 h ${marca}`, vencimiento: dentroDeHoras(5) },
  ]

  await page.goto('/tareas')
  const panel = page.getByRole('dialog', { name: /^(Crear|Editar) tarea$/ })
  for (const tarea of tareas) {
    await page.getByRole('button', { name: 'Crear tarea' }).click()
    await panel.getByPlaceholder('Nombre').fill(tarea.nombre)
    await panel.getByPlaceholder('Descripción').fill('Con vencimiento')
    await panel.locator('#fecha-creacion').fill('01/01/2026 09:00:00')
    await panel.locator('#fecha-vencimiento').fill(tarea.vencimiento)
    await panel.getByRole('button', { name: 'Guardar' }).click()
    await expect(panel).toBeHidden()
  }

  const futura = page.locator('tr', { hasText: tareas[0].nombre }).getByRole('timer')
  await expect(futura).toHaveText(/^Vence en \d+ d \d{2} h \d{2} min \d{2} s$/)
  const antes = await futura.textContent()
  await expect(futura).not.toHaveText(antes!, { timeout: 3000 })

  const pasada = page.locator('tr', { hasText: tareas[1].nombre }).getByRole('timer')
  await expect(pasada).toHaveText(/^Vencida hace \d+ d \d{2} h \d{2} min$/)
  await expect(pasada).toHaveClass(/text-destructive/)

  // Colores según lo que falta: verde (≥ 48 h), naranja (24–48 h), rojo (< 24 h).
  await expect(futura).toHaveAttribute('data-nivel', 'holgada')
  await expect(futura).toHaveClass(/text-green-700/)
  const en30 = page.locator('tr', { hasText: tareas[2].nombre }).getByRole('timer')
  await expect(en30).toHaveAttribute('data-nivel', 'menos-de-48h')
  await expect(en30).toHaveClass(/text-orange-700/)
  const en5 = page.locator('tr', { hasText: tareas[3].nombre }).getByRole('timer')
  await expect(en5).toHaveAttribute('data-nivel', 'menos-de-24h')
  await expect(en5).toHaveClass(/text-destructive/)
  await page.screenshot({ path: 'e2e/capturas/tareas-08-cuenta-atras.png' })

  // En el detalle también aparece la cuenta atrás.
  await page.getByRole('button', { name: `Ver detalle de la tarea ${tareas[0].nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: tareas[0].nombre })
  await expect(detalle.getByRole('timer')).toHaveText(/^Vence en /)
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()
  // Se audita cuando han terminado todas las animaciones (el fondo de la modal
  // se desvanece al cerrarla y, a medias, daba falsos fallos de contraste).
  const sinAnimaciones = () =>
    page.evaluate(() =>
      Promise.all(
        document
          .getAnimations()
          // Las infinitas (indicadores de carga) no terminan nunca.
          .filter((animacion) => animacion.effect?.getTiming().iterations !== Infinity)
          .map((animacion) => animacion.finished),
      ),
    )
  await sinAnimaciones()

  // Accesibilidad con contadores en pantalla, en claro y en oscuro.
  const auditar = () =>
    new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
      .exclude('.vue-devtools__anchor-btn')
      .analyze()
  expect((await auditar()).violations).toEqual([])
  await page.getByRole('switch', { name: 'Cambiar a modo oscuro' }).click()
  await expect(page.locator('html')).toHaveClass(/\bdark\b/)
  await sinAnimaciones()
  expect((await auditar()).violations).toEqual([])
})

test('marca una tarea como completada, la tacha, se conserva al recargar y se desmarca', async ({
  page,
}) => {
  const nombre = `Completable ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog', { name: 'Crear tarea' })
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Se tacha al completarla')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  const conmutador = fila.getByRole('button', { name: `Marcar como completada la tarea ${nombre}` })
  const celdaNombre = fila.locator('td').first()
  await expect(conmutador).toHaveAttribute('aria-pressed', 'false')
  await expect(celdaNombre).toHaveCSS('text-decoration-line', 'none')

  await conmutador.click()
  await expect(conmutador).toHaveAttribute('aria-pressed', 'true')
  await expect(conmutador).toHaveAttribute('title', 'Completada')
  await expect(celdaNombre).toHaveCSS('text-decoration-line', 'line-through')
  await expect(fila.locator('td').last()).toHaveCSS('text-decoration-line', 'none')
  await page.screenshot({ path: 'e2e/capturas/tareas-09-completada.png' })

  // El estado se guarda: sigue tachada al recargar y en el detalle.
  await page.reload()
  await expect(conmutador).toHaveAttribute('aria-pressed', 'true')
  await expect(celdaNombre).toHaveCSS('text-decoration-line', 'line-through')
  await fila.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  await expect(detalle).toContainText('Completada')
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()

  await conmutador.click()
  await expect(conmutador).toHaveAttribute('aria-pressed', 'false')
  await expect(celdaNombre).toHaveCSS('text-decoration-line', 'none')
  await page.reload()
  await expect(conmutador).toHaveAttribute('aria-pressed', 'false')
})

test('crea subtareas y comentarios desde el detalle de la tarea', async ({ page }) => {
  const nombre = `Con subtareas ${Date.now()}`

  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const panel = page.getByRole('dialog', { name: 'Crear tarea' })
  await panel.getByPlaceholder('Nombre').fill(nombre)
  await panel.getByPlaceholder('Descripción').fill('Para subtareas y comentarios')
  await panel.getByRole('button', { name: 'Guardar' }).click()
  await expect(panel).toBeHidden()

  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  await expect(detalle.getByText('Esta tarea no tiene subtareas.')).toBeVisible()
  await expect(detalle.getByText('Todavía no hay comentarios.')).toBeVisible()

  // Subtareas: dos altas seguidas (la fila queda abierta tras guardar).
  await detalle.getByRole('button', { name: 'Añadir subtarea' }).click()
  await detalle.getByLabel('Nombre de la subtarea').fill('Subtarea 1')
  await detalle.getByLabel('Persona asignada').fill(`Ana ${nombre}`)
  await detalle.getByLabel('Prioridad de la subtarea').fill('2')
  await detalle.getByRole('button', { name: 'Guardar' }).click()
  await expect(detalle.getByTestId('contador-subtareas')).toHaveText('1 sin resolver')
  await detalle.getByLabel('Nombre de la subtarea').fill('Subtarea 2')
  await detalle.getByRole('button', { name: 'Guardar' }).click()
  await expect(detalle.getByTestId('contador-subtareas')).toHaveText('2 sin resolver')

  const resolver = detalle.getByRole('button', {
    name: 'Marcar como resuelta la subtarea Subtarea 1',
  })
  await resolver.click()
  await expect(resolver).toHaveAttribute('aria-pressed', 'true')
  await expect(detalle.getByTestId('contador-subtareas')).toHaveText('1 sin resolver')

  await detalle.getByRole('button', { name: 'Eliminar subtarea Subtarea 2' }).click()
  await detalle
    .getByRole('group', { name: '¿Eliminar la subtarea Subtarea 2?' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(detalle.getByText('Subtarea 2')).toHaveCount(0)

  // Comentarios: con el botón y con Ctrl+Enter, respetando saltos de línea.
  const campo = detalle.getByRole('textbox', { name: 'Escribe un comentario' })
  await campo.fill('Primer comentario\ncon dos líneas')
  await detalle.getByRole('button', { name: 'Enviar comentario' }).click()
  await expect(campo).toHaveValue('')
  await campo.fill('Segundo comentario')
  await campo.press('Control+Enter')
  const historial = detalle.getByRole('list', { name: 'Historial de comentarios' })
  await expect(historial).toContainText('Primer comentario')
  await expect(historial).toContainText('Segundo comentario')
  await expect(historial.locator('time').first()).toHaveText(/^\d{2}:\d{2}$/)
  await page.screenshot({ path: 'e2e/capturas/tareas-10-subtareas-comentarios.png' })

  // Todo se guarda: sigue igual al cerrar y volver a abrir.
  await page.keyboard.press('Escape')
  await expect(detalle).toBeHidden()
  await page.reload()
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  await expect(detalle.getByTestId('contador-subtareas')).toHaveText('0 sin resolver')
  await expect(
    detalle.getByRole('button', { name: 'Marcar como resuelta la subtarea Subtarea 1' }),
  ).toHaveAttribute('aria-pressed', 'true')
  await expect(historial).toContainText('Segundo comentario')
})

// Regresiones de accesibilidad de los comentarios: con muchos comentarios el
// historial desplazable debe poder enfocarse, y al enviar con el botón el foco
// no debe perderse.
test('el historial de comentarios largo es accesible y enviar con el botón mantiene el foco', async ({
  page,
  request,
}) => {
  const nombre = `Muchos comentarios ${Date.now()}`
  const creada = await request.post('/api/v1/tareas', {
    data: { nombre, descripcion: 'Con historial largo', fecha_creacion: '2026-01-01T09:00:00' },
  })
  expect(creada.status()).toBe(201)
  const { id } = (await creada.json()) as { id: number }
  for (let i = 1; i <= 17; i += 1) {
    const respuesta = await request.post(`/api/v1/tareas/${id}/comentarios`, {
      data: { texto: `Comentario número ${i}` },
    })
    expect(respuesta.status()).toBe(201)
  }

  await page.goto('/tareas')
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  await expect(detalle.getByText('Comentario número 17')).toBeVisible()
  await detalle.evaluate((elemento) =>
    Promise.all(elemento.getAnimations().map((animacion) => animacion.finished)),
  )

  const resultado = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .exclude('.vue-devtools__anchor-btn')
    .analyze()
  expect(resultado.violations).toEqual([])

  const campo = detalle.getByRole('textbox', { name: 'Escribe un comentario' })
  await campo.fill('Enviado con el botón')
  await detalle.getByRole('button', { name: 'Enviar comentario' }).focus()
  await page.keyboard.press('Enter')
  await expect(detalle.getByText('Enviado con el botón')).toBeVisible()
  await expect(campo).toBeFocused()
})

test('edita y borra subtareas y comentarios pidiendo confirmación', async ({ page, request }) => {
  const nombre = `Editable ${Date.now()}`
  const creada = await request.post('/api/v1/tareas', {
    data: { nombre, descripcion: 'Para editar y borrar', fecha_creacion: '2026-01-01T09:00:00' },
  })
  const { id } = (await creada.json()) as { id: number }
  expect(
    (
      await request.post(`/api/v1/tareas/${id}/subtareas`, { data: { nombre: 'Original' } })
    ).status(),
  ).toBe(201)
  expect(
    (
      await request.post(`/api/v1/tareas/${id}/comentarios`, {
        data: { texto: 'Comentario original' },
      })
    ).status(),
  ).toBe(201)

  await page.goto('/tareas')
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })

  // Subtarea: editar exige confirmar; cancelar la confirmación no guarda.
  await detalle.getByRole('button', { name: 'Editar subtarea Original' }).click()
  await detalle.getByLabel('Nuevo nombre de la subtarea Original').fill('Renombrada')
  await detalle.getByLabel('Nueva prioridad de la subtarea Original').fill('3')
  await detalle.getByRole('button', { name: 'Guardar', exact: true }).click()
  const confirmarSubtarea = detalle.getByRole('group', {
    name: '¿Guardar los cambios de la subtarea Original?',
  })
  await expect(confirmarSubtarea).toBeVisible()
  await confirmarSubtarea.getByRole('button', { name: 'Guardar' }).click()
  await expect(detalle.getByRole('button', { name: 'Editar subtarea Renombrada' })).toBeVisible()
  await expect(detalle.getByText('Original', { exact: true })).toHaveCount(0)

  // Comentario: editar con confirmación y marca "(editado)".
  await detalle.getByRole('button', { name: /^Editar comentario de las / }).click()
  await detalle
    .getByRole('textbox', { name: 'Nuevo texto del comentario' })
    .fill('Comentario corregido')
  await detalle
    .getByRole('form', { name: 'Editar comentario' })
    .getByRole('button', { name: 'Guardar' })
    .click()
  const confirmarComentario = detalle.getByRole('group', {
    name: '¿Guardar los cambios del comentario?',
  })
  await confirmarComentario.getByRole('button', { name: 'Guardar' }).click()
  await expect(detalle.getByText('Comentario corregido')).toBeVisible()
  // Visible: "(editado)"; el texto completo incluye la fecha para lectores de pantalla.
  await expect(detalle.getByTestId('marca-editado')).toHaveText(
    /^\(editado( el .+ a las \d{2}:\d{2})?\)$/,
  )
  await page.screenshot({ path: 'e2e/capturas/tareas-11-editar-borrar.png' })

  // Borrar con confirmación: cancelar conserva, eliminar borra.
  await detalle.getByRole('button', { name: /^Eliminar comentario de las / }).click()
  const confirmarBorrado = detalle.getByRole('group', { name: '¿Eliminar el comentario?' })
  await confirmarBorrado.getByRole('button', { name: 'Cancelar' }).click()
  await expect(detalle.getByText('Comentario corregido')).toBeVisible()
  await detalle.getByRole('button', { name: /^Eliminar comentario de las / }).click()
  await confirmarBorrado.getByRole('button', { name: 'Eliminar' }).click()
  await expect(detalle.getByText('Todavía no hay comentarios.')).toBeVisible()

  await detalle.getByRole('button', { name: 'Eliminar subtarea Renombrada' }).click()
  await detalle
    .getByRole('group', { name: '¿Eliminar la subtarea Renombrada?' })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(detalle.getByText('Esta tarea no tiene subtareas.')).toBeVisible()

  // Se guarda: tras recargar sigue igual.
  await page.keyboard.press('Escape')
  await page.reload()
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  await expect(detalle.getByText('Esta tarea no tiene subtareas.')).toBeVisible()
  await expect(detalle.getByText('Todavía no hay comentarios.')).toBeVisible()
})

test('en pantallas estrechas muestra las subtareas como tarjetas sin desbordar', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  const nombre = `Tarjetas ${Date.now()}`
  const creada = await request.post('/api/v1/tareas', {
    data: { nombre, descripcion: 'Vista móvil', fecha_creacion: '2026-01-01T09:00:00' },
  })
  const { id } = (await creada.json()) as { id: number }
  expect(
    (
      await request.post(`/api/v1/tareas/${id}/subtareas`, {
        data: { nombre: 'Comprar cajas', asignado: 'Ana', prioridad: 2 },
      })
    ).status(),
  ).toBe(201)

  await page.goto('/tareas')
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })
  const tarjetas = detalle.getByTestId('tarjetas-subtareas')
  await expect(tarjetas).toBeVisible()
  await expect(detalle.getByTestId('tabla-subtareas')).toHaveCount(0)
  await expect(tarjetas.getByTestId('tarjeta-subtarea')).toContainText('Ana')

  const sinDesbordar = async (): Promise<boolean> =>
    tarjetas.evaluate((elemento) => elemento.scrollWidth <= elemento.clientWidth)
  expect(await sinDesbordar()).toBe(true)

  await detalle.getByRole('button', { name: 'Editar subtarea Comprar cajas' }).click()
  const campo = detalle.getByLabel('Nuevo nombre de la subtarea Comprar cajas')
  await expect(campo).toBeVisible()
  expect(await sinDesbordar()).toBe(true)
  const caja = await campo.boundingBox()
  const cajaDialogo = await detalle.boundingBox()
  expect(caja && cajaDialogo && caja.x + caja.width <= cajaDialogo.x + cajaDialogo.width).toBe(true)
  await page.screenshot({ path: 'e2e/capturas/tareas-12-subtareas-movil.png' })

  await campo.fill('Comprar cajas grandes')
  await detalle.getByRole('button', { name: 'Guardar', exact: true }).click()
  await detalle
    .getByRole('group', { name: '¿Guardar los cambios de la subtarea Comprar cajas?' })
    .getByRole('button', { name: 'Guardar' })
    .click()
  await expect(
    detalle.getByRole('button', { name: 'Editar subtarea Comprar cajas grandes' }),
  ).toBeVisible()
})

test('comenta una subtarea y borra la tarea pidiendo confirmación', async ({ page, request }) => {
  const nombre = `Borrable ${Date.now()}`
  const creada = await request.post('/api/v1/tareas', {
    data: { nombre, descripcion: 'Para comentar y borrar', fecha_creacion: '2026-01-01T09:00:00' },
  })
  const { id } = (await creada.json()) as { id: number }
  expect(
    (
      await request.post(`/api/v1/tareas/${id}/subtareas`, { data: { nombre: 'Revisar' } })
    ).status(),
  ).toBe(201)

  await page.goto('/tareas')
  await page.getByRole('button', { name: `Ver detalle de la tarea ${nombre}` }).click()
  const detalle = page.getByRole('dialog', { name: nombre })

  // Comentarios de la subtarea, con su contador.
  const botonComentarios = detalle.getByRole('button', {
    name: /^Comentarios de la subtarea Revisar/,
  })
  await botonComentarios.click()
  await expect(botonComentarios).toHaveAttribute('aria-expanded', 'true')
  await detalle
    .getByRole('textbox', { name: 'Escribe un comentario de la subtarea Revisar' })
    .fill('Falta la parte dos')
  await detalle.getByRole('button', { name: 'Enviar comentario de la subtarea Revisar' }).click()
  await expect(detalle.getByTestId('comentarios-subtarea')).toContainText('Falta la parte dos')
  await expect(detalle.getByTestId('numero-comentarios-subtarea')).toHaveText('1')
  await page.screenshot({ path: 'e2e/capturas/tareas-13-comentarios-subtarea.png' })

  // Borrar desde el detalle: cancelar conserva, eliminar borra y cierra.
  await detalle.getByRole('button', { name: `Eliminar la tarea ${nombre}` }).click()
  const confirmar = page.getByRole('alertdialog', { name: `¿Eliminar la tarea ${nombre}?` })
  await expect(confirmar).toContainText('También se eliminarán sus subtareas y comentarios.')
  await confirmar.getByRole('button', { name: 'Cancelar' }).click()
  await expect(confirmar).toBeHidden()
  await expect(detalle).toBeVisible()
  await detalle.getByRole('button', { name: `Eliminar la tarea ${nombre}` }).click()
  await confirmar.getByRole('button', { name: 'Eliminar' }).click()
  await expect(detalle).toBeHidden()
  await expect(page.locator('tr', { hasText: nombre })).toHaveCount(0)
  expect((await request.get(`/api/v1/tareas/${id}/comentarios`)).status()).toBe(404)
  await page.reload()
  await expect(page.locator('tr', { hasText: nombre })).toHaveCount(0)
})

test('crea la tarea en una ventana modal y la borra desde la lista', async ({ page }) => {
  const nombre = `Modal ${Date.now()}`
  await page.goto('/tareas')
  await page.getByRole('button', { name: 'Crear tarea' }).click()
  const ventana = page.getByRole('dialog', { name: 'Crear tarea' })
  await expect(ventana).toHaveAttribute('data-slot', 'dialog-content')
  await ventana.getByPlaceholder('Nombre').fill(nombre)
  await ventana.getByPlaceholder('Descripción').fill('Creada en la ventana modal')
  await page.screenshot({ path: 'e2e/capturas/tareas-14-crear-modal.png' })
  await ventana.getByRole('button', { name: 'Guardar' }).click()
  await expect(ventana).toBeHidden()

  const fila = page.locator('tr', { hasText: nombre })
  await fila.getByRole('button', { name: `Eliminar la tarea ${nombre}` }).click()
  await page
    .getByRole('alertdialog', { name: `¿Eliminar la tarea ${nombre}?` })
    .getByRole('button', { name: 'Eliminar' })
    .click()
  await expect(fila).toHaveCount(0)
})

test('filtra por estado: todas, completadas o no completadas', async ({ page, request }) => {
  const marca = Date.now()
  const hecha = `Hecha ${marca}`
  const pendiente = `Pendiente ${marca}`
  const crear = (nombre: string) =>
    request.post('/api/v1/tareas', {
      data: { nombre, descripcion: 'Filtro de estado', fecha_creacion: '2026-01-01T09:00:00' },
    })
  const respuestaHecha = await crear(hecha)
  expect(respuestaHecha.status()).toBe(201)
  expect((await crear(pendiente)).status()).toBe(201)
  const { id } = (await respuestaHecha.json()) as { id: number }
  const completar = await request.patch(`/api/v1/tareas/${id}/completada`, {
    data: { completada: true },
  })
  expect(completar.status()).toBe(200)

  await page.goto('/tareas')
  await page.getByLabel('Buscar').fill(String(marca))
  const estado = page.getByRole('radiogroup', { name: 'Estado' })
  const fila = (nombre: string) => page.locator('tr', { hasText: nombre })
  await expect(estado.getByRole('radio', { name: 'Todas', exact: true })).toBeChecked()
  await expect(fila(hecha)).toHaveCount(1)
  await expect(fila(pendiente)).toHaveCount(1)

  await estado.getByRole('radio', { name: 'Completadas', exact: true }).check()
  await expect(fila(hecha)).toHaveCount(1)
  await expect(fila(pendiente)).toHaveCount(0)

  await estado.getByRole('radio', { name: 'No completadas', exact: true }).check()
  await expect(fila(hecha)).toHaveCount(0)
  await expect(fila(pendiente)).toHaveCount(1)
  await page.screenshot({ path: 'e2e/capturas/tareas-15-filtro-estado.png' })

  await page.getByRole('button', { name: 'Limpiar filtros' }).click()
  await expect(estado.getByRole('radio', { name: 'Todas', exact: true })).toBeChecked()
})
