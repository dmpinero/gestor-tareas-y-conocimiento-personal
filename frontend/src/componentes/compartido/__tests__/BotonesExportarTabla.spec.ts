import { mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import BotonesExportarTabla from '@/componentes/compartido/BotonesExportarTabla.vue'
import { exportarTablaExcel, exportarTablaPDF } from '@/lib/exportarTabla'

vi.mock('@/lib/exportarTabla', () => ({
  exportarTablaExcel: vi.fn<(...argumentos: unknown[]) => Promise<void>>(),
  exportarTablaPDF: vi.fn<(...argumentos: unknown[]) => Promise<void>>(),
}))

const propiedades = {
  nombreFichero: 'Tareas',
  titulo: 'Tareas',
  columnas: ['Nombre', 'Prioridad'],
  filas: [['Comprar pan', 1]],
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers()
  vi.setSystemTime(new Date(2026, 0, 5, 9, 3, 7))
})

afterEach(() => {
  vi.useRealTimers()
})

describe('BotonesExportarTabla', () => {
  it('muestra los botones con nombre accesible y título', () => {
    const envoltorio = mount(BotonesExportarTabla, { props: propiedades })

    const excel = envoltorio.get('button[aria-label="Exportar a Excel"]')
    const pdf = envoltorio.get('button[aria-label="Exportar a PDF"]')
    expect(excel.attributes('title')).toBe('Exportar a Excel')
    expect(pdf.attributes('title')).toBe('Exportar a PDF')
  })

  it('Exportar a Excel llama a exportarTablaExcel con el nombre y la marca temporal', async () => {
    const envoltorio = mount(BotonesExportarTabla, { props: propiedades })

    await envoltorio.get('[aria-label="Exportar a Excel"]').trigger('click')

    expect(exportarTablaExcel).toHaveBeenCalledWith(
      'Tareas_05012026_090307.xlsx',
      propiedades.columnas,
      propiedades.filas,
    )
    expect(exportarTablaPDF).not.toHaveBeenCalled()
  })

  it('Exportar a PDF llama a exportarTablaPDF con el nombre, la marca temporal, el título y los datos', async () => {
    const envoltorio = mount(BotonesExportarTabla, { props: propiedades })

    await envoltorio.get('[aria-label="Exportar a PDF"]').trigger('click')

    expect(exportarTablaPDF).toHaveBeenCalledWith(
      'Tareas_05012026_090307.pdf',
      'Tareas',
      propiedades.columnas,
      propiedades.filas,
    )
    expect(exportarTablaExcel).not.toHaveBeenCalled()
  })
})
