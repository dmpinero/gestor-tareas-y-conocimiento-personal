<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import type { DatosTarea, Tarea } from '@/api/tipos'
import { aFechaHoraIso, formatearFechaHora, PATRON_FECHA_HORA } from '@/lib/fechas'
import { useTiendaTareas } from '@/stores/tareas'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/componentes/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/componentes/ui/table'
import { Textarea } from '@/componentes/ui/textarea'

const tienda = useTiendaTareas()
const panelAbierto = ref(false)
const errorFormulario = ref<string | null>(null)
// `null` en modo crear; el id de la tarea en modo editar.
const idEnEdicion = ref<number | null>(null)

const ERROR_FECHA_HORA = 'La fecha y hora debe tener el formato dd/mm/aaaa hh:mm:ss y ser válida.'

// La prioridad llega como número desde un `<input type="number">`, o como
// cadena vacía cuando el campo se deja en blanco.
const formulario = reactive<{
  nombre: string
  prioridad: string | number | null
  descripcion: string
  fechaHora: string
}>({ nombre: '', prioridad: '', descripcion: '', fechaHora: '' })

onMounted(() => {
  void tienda.cargar()
})

function limpiarFormulario(): void {
  formulario.nombre = ''
  formulario.prioridad = ''
  formulario.descripcion = ''
  formulario.fechaHora = ''
  errorFormulario.value = null
  idEnEdicion.value = null
}

function abrirParaCrear(): void {
  limpiarFormulario()
  formulario.fechaHora = formatearFechaHora(new Date())
  panelAbierto.value = true
}

function abrirParaEditar(tarea: Tarea): void {
  limpiarFormulario()
  idEnEdicion.value = tarea.id
  formulario.nombre = tarea.nombre
  formulario.prioridad = tarea.prioridad ?? ''
  formulario.descripcion = tarea.descripcion
  formulario.fechaHora = formatearFechaHora(tarea.fecha_hora)
  panelAbierto.value = true
}

function aPrioridad(valor: string | number | null): number | null {
  if (valor === null || valor === '') return null
  return Number(valor)
}

async function guardar(): Promise<void> {
  errorFormulario.value = null
  const fechaHora = aFechaHoraIso(formulario.fechaHora)
  if (fechaHora === null) {
    errorFormulario.value = ERROR_FECHA_HORA
    return
  }
  const datos: DatosTarea = {
    nombre: formulario.nombre,
    prioridad: aPrioridad(formulario.prioridad),
    descripcion: formulario.descripcion,
    fecha_hora: fechaHora,
  }
  try {
    if (idEnEdicion.value === null) {
      await tienda.crear(datos)
    } else {
      await tienda.actualizar(idEnEdicion.value, datos)
    }
    panelAbierto.value = false
    limpiarFormulario()
  } catch (motivo) {
    errorFormulario.value = (motivo as Error).message
  }
}
</script>

<template>
  <section>
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">Tareas</h2>
      <Button variant="success" @click="abrirParaCrear">Crear tarea</Button>
    </div>

    <Sheet v-model:open="panelAbierto">
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{{ idEnEdicion === null ? 'Crear tarea' : 'Editar tarea' }}</SheetTitle>
        </SheetHeader>

        <form class="flex flex-col gap-3 px-4" @submit.prevent="guardar">
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-nombre">Nombre</Label>
            <Input
              id="tarea-nombre"
              v-model="formulario.nombre"
              placeholder="Nombre"
              required
              maxlength="200"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-prioridad">Prioridad</Label>
            <Input
              id="tarea-prioridad"
              v-model="formulario.prioridad"
              type="number"
              min="1"
              max="5"
              placeholder="Prioridad"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-descripcion">Descripción</Label>
            <Textarea
              id="tarea-descripcion"
              v-model="formulario.descripcion"
              placeholder="Descripción"
              required
              maxlength="500"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <Label for="tarea-fecha-hora">Fecha y hora</Label>
            <Input
              id="tarea-fecha-hora"
              v-model="formulario.fechaHora"
              placeholder="dd/mm/aaaa hh:mm:ss"
              required
              :pattern="PATRON_FECHA_HORA"
            />
          </div>

          <p v-if="errorFormulario" class="text-sm text-destructive" role="alert">
            {{ errorFormulario }}
          </p>

          <div class="flex gap-2">
            <Button type="submit" variant="success">Guardar</Button>
            <Button type="button" variant="destructive" @click="panelAbierto = false"
              >Cancelar</Button
            >
          </div>
        </form>
      </SheetContent>
    </Sheet>

    <p v-if="tienda.error" class="mt-2 text-sm text-destructive" role="alert">{{ tienda.error }}</p>

    <p
      v-if="!tienda.cargando && tienda.tareas.length === 0"
      class="text-muted-foreground mt-4 text-sm"
    >
      Todavía no hay tareas.
    </p>
    <Table v-else-if="tienda.tareas.length > 0" class="mt-4">
      <TableHeader>
        <TableRow>
          <TableHead>Nombre</TableHead>
          <TableHead>Prioridad</TableHead>
          <TableHead>Descripción</TableHead>
          <TableHead>Fecha y hora</TableHead>
          <TableHead><span class="sr-only">Acciones</span></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow v-for="tarea in tienda.tareas" :key="tarea.id">
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            tarea.nombre
          }}</TableCell>
          <TableCell>{{ tarea.prioridad ?? '—' }}</TableCell>
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            tarea.descripcion
          }}</TableCell>
          <TableCell class="whitespace-normal [overflow-wrap:anywhere]">{{
            formatearFechaHora(tarea.fecha_hora)
          }}</TableCell>
          <TableCell>
            <Button
              variant="outline"
              size="sm"
              :aria-label="`Editar tarea ${tarea.nombre}`"
              @click="abrirParaEditar(tarea)"
              >Editar</Button
            >
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  </section>
</template>
