<script setup lang="ts">
import { CircleHelp } from '@lucide/vue'
import { Button } from '@/componentes/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/componentes/ui/popover'
import ModalChangelog from './ModalChangelog.vue'
</script>

<template>
  <Popover>
    <PopoverTrigger as-child>
      <Button variant="ghost" size="icon" aria-label="Ayuda: historial de cambios">
        <CircleHelp class="size-4" />
      </Button>
    </PopoverTrigger>
    <PopoverContent class="w-56 p-1" align="end">
      <ModalChangelog />
    </PopoverContent>
  </Popover>
</template>
