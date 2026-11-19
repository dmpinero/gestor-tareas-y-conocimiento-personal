<script setup lang="ts">
import { BookOpen, BriefcaseBusiness, House, ListTodo, Settings2 } from '@lucide/vue'
import { computed, type Component } from 'vue'
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
import { useNombreMenuAlta } from '@/composables/useNombreMenuAlta'

interface ElementoNavegacion {
  a: string
  etiqueta: string
  icono: Component
  color: string
  /** Subapartados que se muestran debajo (ocultos con el panel colapsado). */
  hijos?: SubElementoNavegacion[]
}

/** Un subapartado es un enlace o un grupo sin página propia con sus enlaces. */
type SubElementoNavegacion =
  | { a: string; etiqueta: string; icono: Component; color: string }
  | { etiqueta: string; icono: Component; color: string; enlaces: EnlaceGrupo[] }

interface EnlaceGrupo {
  a: string
  etiqueta: string
}

interface GrupoNavegacion {
  titulo: string
  elementos: ElementoNavegacion[]
}

const ruta = useRoute()
const nombreMenuAlta = useNombreMenuAlta()

const grupos = computed<GrupoNavegacion[]>(() => [
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
            etiqueta: 'Oportunidades',
            icono: BriefcaseBusiness,
            color: 'text-amber-500',
            enlaces: [{ a: '/tareas/oportunidades', etiqueta: nombreMenuAlta.value }],
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
])

function estaActivo(destino: string): boolean {
  if (destino === '/') return ruta.path === '/'
  return ruta.path === destino || ruta.path.startsWith(`${destino}/`)
}

function destinos(hijo: SubElementoNavegacion): string[] {
  return 'enlaces' in hijo ? hijo.enlaces.map((enlace) => enlace.a) : [hijo.a]
}

/** Página actual: la sección activa, salvo que lo esté uno de sus subapartados. */
function esPaginaActual(elemento: ElementoNavegacion): boolean {
  return (
    estaActivo(elemento.a) &&
    !elemento.hijos?.some((hijo) => destinos(hijo).some((destino) => estaActivo(destino)))
  )
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
                <SidebarMenuSubItem v-for="hijo in elemento.hijos" :key="hijo.etiqueta">
                  <!-- Grupo sin página propia: un rótulo con sus enlaces debajo. -->
                  <template v-if="'enlaces' in hijo">
                    <span
                      :data-grupo-menu="hijo.etiqueta"
                      class="text-sidebar-foreground flex h-7 items-center gap-2 px-2 text-sm [&>svg]:size-4 [&>svg]:shrink-0"
                    >
                      <component :is="hijo.icono" :class="hijo.color" aria-hidden="true" />
                      <span>{{ hijo.etiqueta }}</span>
                    </span>
                    <SidebarMenuSub>
                      <SidebarMenuSubItem v-for="enlace in hijo.enlaces" :key="enlace.a">
                        <SidebarMenuSubButton as-child :is-active="estaActivo(enlace.a)">
                          <RouterLink
                            :to="enlace.a"
                            :aria-current="estaActivo(enlace.a) ? 'page' : undefined"
                          >
                            <span>{{ enlace.etiqueta }}</span>
                          </RouterLink>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    </SidebarMenuSub>
                  </template>
                  <SidebarMenuSubButton v-else as-child :is-active="estaActivo(hijo.a)">
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
