/** Descarga un `Blob` en el navegador con el nombre de fichero indicado. */
export function descargarBlob(blob: Blob, nombreFichero: string): void {
  const url = URL.createObjectURL(blob)
  const enlace = document.createElement('a')
  enlace.href = url
  enlace.download = nombreFichero
  enlace.click()
  URL.revokeObjectURL(url)
}
