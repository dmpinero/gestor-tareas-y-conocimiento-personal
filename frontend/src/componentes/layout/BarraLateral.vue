<script setup lang="ts">
import { BookOpen, House, ListTodo, Settings2 } from '@lucide/vue'
import type { Component } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from '@/componentes/ui/sidebar'

interface ElementoNavegacion {
  a: string
  etiqueta: string
  icono: Component
  color: string
}

interface GrupoNavegacion {
  titulo: string
  elementos: ElementoNavegacion[]
}

const ruta = useRoute()

const grupos: GrupoNavegacion[] = [
  {
    titulo: 'General',
    elementos: [
      { a: '/', etiqueta: 'Inicio', icono: House, color: 'text-blue-500' },
      { a: '/tareas', etiqueta: 'Tareas', icono: ListTodo, color: 'text-rose-500' },
      { a: '/conocimiento', etiqueta: 'Conocimiento', icono: BookOpen, color: 'text-cyan-500' },
    ],
  },
  {
    titulo: 'Configuración',
    elementos: [{ a: '/ajustes', etiqueta: 'Ajustes', icono: Settings2, color: 'text-violet-500' }],
  },
]

function estaActivo(destino: string): boolean {
  if (destino === '/') return ruta.path === '/'
  return ruta.path === destino || ruta.path.startsWith(`${destino}/`)
}
</script>

<template>
  <Sidebar side="left" collapsible="icon">
    <SidebarHeader class="flex flex-row items-center justify-start">
      <SidebarTrigger />
    </SidebarHeader>
    <SidebarContent>
      <SidebarGroup v-for="grupo in grupos" :key="grupo.titulo">
        <SidebarGroupLabel>{{ grupo.titulo }}</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem v-for="elemento in grupo.elementos" :key="elemento.a">
              <SidebarMenuButton
                as-child
                :is-active="estaActivo(elemento.a)"
                :tooltip="elemento.etiqueta"
              >
                <RouterLink
                  :to="elemento.a"
                  :aria-current="estaActivo(elemento.a) ? 'page' : undefined"
                >
                  <component :is="elemento.icono" :class="elemento.color" />
                  <span>{{ elemento.etiqueta }}</span>
                </RouterLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  </Sidebar>
</template>
