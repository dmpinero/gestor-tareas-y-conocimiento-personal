import excelJS from 'exceljs'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { descargarBlob } from '@/lib/descargas'
import { exportarTablaExcel, exportarTablaPDF } from '@/lib/exportarTabla'

vi.mock('@/lib/descargas', () => ({
  descargarBlob: vi.fn<(blob: Blob, nombreFichero: string) => void>(),
}))

const { constructorPdf, textoPdf, tamanoLetraPdf, guardarPdf, tablaAutomatica } = vi.hoisted(
  () => ({
    constructorPdf: vi.fn<(opciones: unknown) => void>(),
    textoPdf: vi.fn<(texto: string, x: number, y: number) => void>(),
    tamanoLetraPdf: vi.fn<(tamano: number) => void>(),
    guardarPdf: vi.fn<(nombre: string) => void>(),
    tablaAutomatica: vi.fn<(documento: unknown, opciones: unknown) => void>(),
  }),
)

vi.mock('jspdf', () => ({
  jsPDF: vi.fn<(opciones: unknown) => object>().mockImplementation(function (opciones: unknown) {
    constructorPdf(opciones)
    return { setFontSize: tamanoLetraPdf, text: textoPdf, save: guardarPdf }
  }),
}))
vi.mock('jspdf-autotable', () => ({ default: tablaAutomatica }))

const columnas = ['Nombre', 'Prioridad', 'Fecha y hora']
const filas: (string | number)[][] = [
  ['Comprar pan', 1, '05/01/2026 09:03:07'],
  ['Llamar al médico', '—', '06/01/2026 10:00:00'],
]

beforeEach(() => {
  vi.clearAllMocks()
})

describe('exportarTablaExcel', () => {
  it('descarga un libro con la hoja Datos, la cabecera en negrita y las filas indicadas', async () => {
    await exportarTablaExcel('Tareas_05012026_090307.xlsx', columnas, filas)

    expect(descargarBlob).toHaveBeenCalledOnce()
    const [blob, nombreFichero] = vi.mocked(descargarBlob).mock.calls[0] as [Blob, string]
    expect(nombreFichero).toBe('Tareas_05012026_090307.xlsx')
    expect(blob.type).toBe('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    const libro = new excelJS.Workbook()
    await libro.xlsx.load(await blob.arrayBuffer())
    const hoja = libro.getWorksheet('Datos')
    expect(hoja).toBeDefined()
    expect(hoja?.rowCount).toBe(3)
    expect(hoja?.getRow(1).values).toEqual([undefined, ...columnas])
    expect(hoja?.getRow(1).font?.bold).toBe(true)
    expect(hoja?.getRow(2).values).toEqual([undefined, ...filas[0]!])
    expect(hoja?.getRow(3).values).toEqual([undefined, ...filas[1]!])
  })
})

describe('exportarTablaPDF', () => {
  it('crea un PDF apaisado con el título y la tabla, y lo guarda con el nombre indicado', async () => {
    await exportarTablaPDF('Tareas_05012026_090307.pdf', 'Tareas', columnas, filas)

    expect(constructorPdf).toHaveBeenCalledWith({ orientation: 'landscape' })
    expect(textoPdf).toHaveBeenCalledWith('Tareas', 14, 15)
    expect(tablaAutomatica).toHaveBeenCalledOnce()
    const [documento, opciones] = tablaAutomatica.mock.calls[0]!
    expect(documento).toEqual(expect.objectContaining({ save: guardarPdf }))
    expect(opciones).toEqual(expect.objectContaining({ head: [columnas], body: filas }))
    expect(guardarPdf).toHaveBeenCalledWith('Tareas_05012026_090307.pdf')
  })
})
