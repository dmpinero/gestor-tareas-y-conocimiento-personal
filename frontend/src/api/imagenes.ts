import { clienteApi } from './cliente'

/** Respuesta de `POST /imagenes`: la imagen guardada para un comentario. */
export interface ImagenSubida {
  id: string
  /** URL relativa (`/api/v1/imagenes/<id>`): la que admite el `src` del comentario. */
  url: string
  tipo: string
  tamano: number
}

/** Tipos de imagen que admite la API (los reconoce por el contenido). */
export const TIPOS_IMAGEN = ['image/png', 'image/jpeg', 'image/gif', 'image/webp']

/** Tamaño máximo de una imagen, como en la API. */
export const TAMANO_MAXIMO_IMAGEN = 5 * 1024 * 1024

/** Sube una imagen (captura de pantalla) para ponerla en un comentario. */
// La API la exige al subir: así una página de otro sitio no puede subir imágenes
// con un formulario o un fetch "simple" (CORS obliga a pedir permiso antes).
const CABECERA_SUBIDA = { 'X-Requested-With': 'gestor-tareas' }

export function subirImagen(fichero: File): Promise<ImagenSubida> {
  return clienteApi.subirArchivo<ImagenSubida>('/imagenes', 'archivo', fichero, CABECERA_SUBIDA)
}
