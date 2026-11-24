import { createRouter, createWebHistory } from 'vue-router'
import VistaInicio from '@/vistas/VistaInicio.vue'
import VistaTareas from '@/vistas/VistaTareas.vue'
import VistaConocimiento from '@/vistas/VistaConocimiento.vue'
import VistaAjustes from '@/vistas/VistaAjustes.vue'
import VistaCodigosServicio from '@/vistas/VistaCodigosServicio.vue'
import VistaGruposEstados from '@/vistas/VistaGruposEstados.vue'
import VistaWorkflows from '@/vistas/VistaWorkflows.vue'
import VistaOportunidades from '@/vistas/VistaOportunidades.vue'
import VistaSubestados from '@/vistas/VistaSubestados.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'inicio',
      component: VistaInicio,
    },
    {
      path: '/tareas',
      name: 'tareas',
      component: VistaTareas,
    },
    // Oportunidades es una sección propia del menú (antes colgaba de Tareas:
    // las rutas antiguas redirigen a las nuevas).
    { path: '/oportunidades', redirect: '/oportunidades/anes' },
    {
      path: '/oportunidades/anes',
      name: 'oportunidades',
      component: VistaOportunidades,
    },
    {
      path: '/oportunidades/axas-ms3',
      name: 'oportunidades-axas-ms3',
      component: VistaOportunidades,
      props: { variante: 'axas-ms3' },
    },
    { path: '/tareas/oportunidades', redirect: '/oportunidades/anes' },
    { path: '/tareas/oportunidades/axas-ms3', redirect: '/oportunidades/axas-ms3' },
    {
      path: '/conocimiento',
      name: 'conocimiento',
      component: VistaConocimiento,
    },
    {
      path: '/ajustes',
      name: 'ajustes',
      component: VistaAjustes,
    },
    {
      path: '/ajustes/workflows',
      name: 'workflows',
      component: VistaWorkflows,
    },
    // Ruta del antiguo "Workflow Oportunidades", ahora uno más de los workflows.
    {
      path: '/ajustes/workflow-oportunidades',
      redirect: '/ajustes/workflows',
    },
    {
      path: '/ajustes/grupos-estados',
      name: 'grupos-estados',
      component: VistaGruposEstados,
    },
    {
      path: '/ajustes/subestados',
      name: 'subestados',
      component: VistaSubestados,
    },
    {
      path: '/ajustes/codigos-servicio',
      name: 'codigos-servicio',
      component: VistaCodigosServicio,
    },
  ],
})

export default router
