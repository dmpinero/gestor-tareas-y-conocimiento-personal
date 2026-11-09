const URL_BASE_API = import.meta.env.VITE_URL_BASE_API ?? '/api/v1'

/** Construye la URL completa de un recurso de la API, para usarla en un
 * enlace directo (p. ej. `<a href>` para ver un adjunto en pestaña nueva)
 * en vez de pasar por `clienteApi.descargar` + Blob. */
export function urlRecurso(ruta: string): string {
  return `${URL_BASE_API}${ruta}`
}

export class ErrorApi extends Error {
  constructor(
    public readonly estado: number,
    mensaje: string,
    public readonly traza?: string,
  ) {
    super(mensaje)
    this.name = 'ErrorApi'
  }
}

interface OpcionesPeticion {
  cuerpo?: unknown
  token?: string | null
}

interface DetalleError {
  mensaje: string
  traza?: string
}

async function extraerDetalleError(respuesta: Response): Promise<DetalleError> {
  try {
    const datos = await respuesta.clone().json()
    const traza = typeof datos.traza === 'string' ? datos.traza : undefined
    if (typeof datos.detalle === 'string') return { mensaje: datos.detalle, traza }
    if (typeof datos.detail === 'string') return { mensaje: datos.detail, traza }
    if (Array.isArray(datos.detail)) {
      return {
        mensaje: datos.detail.map((error: { msg?: string }) => error.msg).join('; '),
        traza,
      }
    }
  } catch {
    // El cuerpo no era JSON; se usa el texto del estado HTTP como mensaje.
  }
  return { mensaje: respuesta.statusText }
}

async function peticion<T>(
  metodo: 'GET' | 'POST' | 'PUT' | 'DELETE',
  ruta: string,
  opciones: OpcionesPeticion = {},
): Promise<T> {
  const cabeceras: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (opciones.token) {
    cabeceras.Authorization = `Bearer ${opciones.token}`
  }

  const opcionesFetch: RequestInit = {
    method: metodo,
    headers: cabeceras,
    ...(opciones.cuerpo ? { body: JSON.stringify(opciones.cuerpo) } : {}),
  }
  const respuesta = await fetch(`${URL_BASE_API}${ruta}`, opcionesFetch)

  if (!respuesta.ok) {
    const { mensaje, traza } = await extraerDetalleError(respuesta)
    throw new ErrorApi(respuesta.status, mensaje, traza)
  }

  if (respuesta.status === 204) {
    return undefined as T
  }

  return (await respuesta.json()) as T
}

async function descargar(ruta: string): Promise<Blob> {
  const respuesta = await fetch(`${URL_BASE_API}${ruta}`)

  if (!respuesta.ok) {
    const { mensaje, traza } = await extraerDetalleError(respuesta)
    throw new ErrorApi(respuesta.status, mensaje, traza)
  }

  return await respuesta.blob()
}

async function subirArchivo<T>(ruta: string, campo: string, fichero: File): Promise<T> {
  const formData = new FormData()
  formData.append(campo, fichero)

  const respuesta = await fetch(`${URL_BASE_API}${ruta}`, {
    method: 'POST',
    body: formData,
  })

  if (!respuesta.ok) {
    const { mensaje, traza } = await extraerDetalleError(respuesta)
    throw new ErrorApi(respuesta.status, mensaje, traza)
  }

  return (await respuesta.json()) as T
}

export const clienteApi = {
  obtener: <T>(ruta: string, token?: string | null) => peticion<T>('GET', ruta, { token }),
  crear: <T>(ruta: string, cuerpo: unknown, token?: string | null) =>
    peticion<T>('POST', ruta, { cuerpo, token }),
  actualizar: <T>(ruta: string, cuerpo: unknown, token?: string | null) =>
    peticion<T>('PUT', ruta, { cuerpo, token }),
  eliminar: <T>(ruta: string, token?: string | null) => peticion<T>('DELETE', ruta, { token }),
  subirArchivo,
  descargar,
}
