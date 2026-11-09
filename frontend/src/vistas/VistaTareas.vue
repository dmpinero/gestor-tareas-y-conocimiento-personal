<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import type { DatosTarea } from '@/api/tipos'
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

// La prioridad llega como número desde un `<input type="number">`, o como
// cadena vacía cuando el campo se deja en blanco.
const formulario = reactive<{
  nombre: string
  prioridad: string | number | null
  descripcion: string
}>({ nombre: '', prioridad: '', descripcion: '' })

onMounted(() => {
  void tienda.cargar()
})

function limpiarFormulario(): void {
  formulario.nombre = ''
  formulario.prioridad = ''
  formulario.descripcion = ''
  errorFormulario.value = null
}

function abrirParaCrear(): void {
  limpiarFormulario()
  panelAbierto.value = true
}

function aPrioridad(valor: string | number | null): number | null {
  if (valor === null || valor === '') return null
  return Number(valor)
}

async function guardar(): Promise<void> {
  errorFormulario.value = null
  const datos: DatosTarea = {
    nombre: formulario.nombre,
    prioridad: aPrioridad(formulario.prioridad),
    descripcion: formulario.descripcion,
  }
  try {
    await tienda.crear(datos)
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
          <SheetTitle>Crear tarea</SheetTitle>
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
        </TableRow>
      </TableBody>
    </Table>
  </section>
</template>
