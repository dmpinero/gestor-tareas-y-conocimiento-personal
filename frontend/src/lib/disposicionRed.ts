// Posiciones de los nodos de la red de tareas, calculadas con d3-force de una
// vez (sin animación) y de forma determinista: la colocación inicial es la
// espiral de d3 en el orden de los nodos y los empujones aleatorios usan un
// generador con semilla fija, así que la misma red da siempre las mismas
// posiciones.
import {
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceX,
  forceY,
  type SimulationLinkDatum,
  type SimulationNodeDatum,
} from 'd3-force'

import type { Red } from './redTareas'

export interface Punto {
  x: number
  y: number
}

/** Rectángulo que contiene todos los nodos (con margen para sus nombres). */
export interface Caja {
  x: number
  y: number
  ancho: number
  alto: number
}

export interface Disposicion {
  /** Posición de cada nodo, en el orden de `red.nodos`. */
  posiciones: Map<string, Punto>
  caja: Caja
}

/** Margen alrededor de cada nodo dentro de la caja: deja sitio a su nombre. */
export const MARGEN_CAJA = 48
const CAJA_VACIA: Caja = { x: -200, y: -150, ancho: 400, alto: 300 }
const ITERACIONES = 300
const SEMILLA = 0x2f6b9a1

interface NodoSimulado extends SimulationNodeDatum {
  id: string
}

// Generador congruencial lineal (el mismo esquema que usa d3) con semilla fija.
function generadorConSemilla(semilla: number): () => number {
  let estado = semilla >>> 0
  return () => {
    estado = (Math.imul(1664525, estado) + 1013904223) >>> 0
    return estado / 4294967296
  }
}

export function disponerRed(red: Red): Disposicion {
  const nodos: NodoSimulado[] = red.nodos.map((nodo) => ({ id: nodo.id }))
  const enlaces: SimulationLinkDatum<NodoSimulado>[] = red.aristas.map((arista) => ({
    source: arista.origen,
    target: arista.destino,
  }))

  const simulacion = forceSimulation(nodos)
    .randomSource(generadorConSemilla(SEMILLA))
    .force(
      'enlaces',
      forceLink<NodoSimulado, SimulationLinkDatum<NodoSimulado>>(enlaces)
        .id((nodo) => nodo.id)
        .distance(70),
    )
    .force('repulsion', forceManyBody().strength(-180))
    .force('choque', forceCollide(28))
    // Mantienen cerca del centro las tareas sueltas y los grupos separados.
    .force('x', forceX(0).strength(0.06))
    .force('y', forceY(0).strength(0.06))
    .stop()
  simulacion.tick(ITERACIONES)

  const posiciones = new Map<string, Punto>()
  for (const nodo of nodos) posiciones.set(nodo.id, { x: nodo.x ?? 0, y: nodo.y ?? 0 })

  return { posiciones, caja: cajaDe([...posiciones.values()]) }
}

function cajaDe(puntos: Punto[]): Caja {
  if (puntos.length === 0) return { ...CAJA_VACIA }
  const xs = puntos.map((punto) => punto.x)
  const ys = puntos.map((punto) => punto.y)
  const x = Math.min(...xs) - MARGEN_CAJA
  const y = Math.min(...ys) - MARGEN_CAJA
  return {
    x,
    y,
    ancho: Math.max(...xs) + MARGEN_CAJA - x,
    alto: Math.max(...ys) + MARGEN_CAJA - y,
  }
}
