<script setup lang="ts">
import { FileSpreadsheet, FileText } from '@lucide/vue'

import { Button } from '@/componentes/ui/button'
import { type CeldaExportada, exportarTablaExcel, exportarTablaPDF } from '@/lib/exportarTabla'
import { formatearMarcaTemporalFichero } from '@/lib/fechas'

// Botones de exportar reutilizables para cualquier tabla: reciben ya las
// columnas y filas tal como se ven en pantalla y delegan la generación del
// fichero en lib/exportarTabla.
const props = defineProps<{
  nombreFichero: string
  titulo: string
  columnas: string[]
  filas: CeldaExportada[][]
}>()

// La marca temporal evita sobrescribir exportaciones anteriores del mismo
// listado e indica cuándo se generó cada fichero.
function nombreConMarcaTemporal(extension: 'xlsx' | 'pdf'): string {
  return `${props.nombreFichero}_${formatearMarcaTemporalFichero()}.${extension}`
}

async function exportarExcel(): Promise<void> {
  await exportarTablaExcel(nombreConMarcaTemporal('xlsx'), props.columnas, props.filas)
}

async function exportarPdf(): Promise<void> {
  await exportarTablaPDF(nombreConMarcaTemporal('pdf'), props.titulo, props.columnas, props.filas)
}
</script>

<template>
  <div class="flex items-center gap-1">
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label="Exportar a Excel"
      title="Exportar a Excel"
      @click="exportarExcel"
    >
      <FileSpreadsheet class="size-4 text-green-600 dark:text-green-500" aria-hidden="true" />
    </Button>
    <Button
      type="button"
      variant="ghost"
      size="icon"
      aria-label="Exportar a PDF"
      title="Exportar a PDF"
      @click="exportarPdf"
    >
      <FileText class="size-4 text-red-600 dark:text-red-500" aria-hidden="true" />
    </Button>
  </div>
</template>
