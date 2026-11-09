import { descargarBlob } from '@/lib/descargas'

/** Valor de una celda exportada, tal como se muestra en la tabla. */
export type CeldaExportada = string | number

const TIPO_EXCEL = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

// exceljs, jspdf y jspdf-autotable son librerías pesadas que solo hacen falta
// al pulsar «exportar»; se cargan con import() dinámico para que no engorden
// el paquete principal de la aplicación.

/** Genera un libro de Excel con una hoja «Datos» y lo descarga. */
export async function exportarTablaExcel(
  nombreFichero: string,
  columnas: string[],
  filas: CeldaExportada[][],
): Promise<void> {
  const { default: excelJS } = await import('exceljs')
  const libro = new excelJS.Workbook()
  const hoja = libro.addWorksheet('Datos')
  hoja.addRow(columnas).font = { bold: true }
  for (const fila of filas) hoja.addRow(fila)
  hoja.columns.forEach((columna) => {
    columna.width = 22
  })

  const contenido = await libro.xlsx.writeBuffer()
  descargarBlob(new Blob([contenido], { type: TIPO_EXCEL }), nombreFichero)
}

/** Genera un PDF apaisado con el título y la tabla, y lo descarga. */
export async function exportarTablaPDF(
  nombreFichero: string,
  titulo: string,
  columnas: string[],
  filas: CeldaExportada[][],
): Promise<void> {
  const [{ jsPDF }, { default: autoTable }] = await Promise.all([
    import('jspdf'),
    import('jspdf-autotable'),
  ])
  const documento = new jsPDF({ orientation: 'landscape' })
  documento.setFontSize(14)
  documento.text(titulo, 14, 15)
  autoTable(documento, { head: [columnas], body: filas, startY: 20 })
  documento.save(nombreFichero)
}
