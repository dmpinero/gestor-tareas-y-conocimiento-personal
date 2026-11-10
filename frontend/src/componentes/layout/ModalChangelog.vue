<script setup lang="ts">
import { History } from '@lucide/vue'
import { useHistorialCambios } from '@/composables/useHistorialCambios'
import { Button } from '@/componentes/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/componentes/ui/dialog'

const { cargando, error, contenidoHtml, cargar: cargarChangelog } = useHistorialCambios()
</script>

<template>
  <Dialog @update:open="(abierto) => abierto && cargarChangelog()">
    <DialogTrigger as-child>
      <Button variant="ghost" class="w-full justify-start gap-2">
        <History class="size-4" />
        Historial de cambios
      </Button>
    </DialogTrigger>
    <DialogContent class="max-h-[80vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle>Historial de cambios</DialogTitle>
        <DialogDescription
          >Lista de cambios publicados en cada versión de la aplicación.</DialogDescription
        >
      </DialogHeader>
      <p v-if="cargando" class="text-muted-foreground text-sm">Cargando…</p>
      <p v-else-if="error" role="alert" class="text-destructive text-sm">{{ error }}</p>
      <div
        v-else-if="contenidoHtml"
        class="text-sm break-words [&_a]:underline [&_code]:break-words [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:first:mt-0 [&_h3]:mt-3 [&_h3]:font-medium [&_li]:ml-4 [&_pre]:break-words [&_pre]:whitespace-pre-wrap [&_ul]:list-disc [&_ul]:space-y-1"
        v-html="contenidoHtml"
      />
    </DialogContent>
  </Dialog>
</template>
