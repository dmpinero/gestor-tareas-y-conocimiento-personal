<script setup lang="ts">
import { BookOpen, BriefcaseBusiness, House, ListTodo, Settings2 } from '@lucide/vue'
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
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarTrigger,
} from '@/componentes/ui/sidebar'

interface ElementoNavegacion {
  a: string
  etiqueta: string
  icono: Component
  color: string
  /** Subapartados que se muestran debajo (ocultos con el panel colapsado). */
  hijos?: ElementoNavegacion[]
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
      {
        a: '/tareas',
        etiqueta: 'Tareas',
        icono: ListTodo,
        color: 'text-rose-500',
        hijos: [
          {
            a: '/tareas/oportunidades',
            etiqueta: 'Oportunidades',
            icono: BriefcaseBusiness,
            color: 'text-amber-500',
          },
        ],
      },
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

/** Página actual: la sección activa, salvo que lo esté uno de sus subapartados. */
function esPaginaActual(elemento: ElementoNavegacion): boolean {
  return estaActivo(elemento.a) && !elemento.hijos?.some((hijo) => estaActivo(hijo.a))
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
                  :aria-current="esPaginaActual(elemento) ? 'page' : undefined"
                >
                  <component :is="elemento.icono" :class="elemento.color" />
                  <span>{{ elemento.etiqueta }}</span>
                </RouterLink>
              </SidebarMenuButton>
              <SidebarMenuSub v-if="elemento.hijos?.length">
                <SidebarMenuSubItem v-for="hijo in elemento.hijos" :key="hijo.a">
                  <SidebarMenuSubButton as-child :is-active="estaActivo(hijo.a)">
                    <RouterLink
                      :to="hijo.a"
                      :aria-current="estaActivo(hijo.a) ? 'page' : undefined"
                    >
                      <component :is="hijo.icono" :class="hijo.color" aria-hidden="true" />
                      <span>{{ hijo.etiqueta }}</span>
                    </RouterLink>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  </Sidebar>
</template>
