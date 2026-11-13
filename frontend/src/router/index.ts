import { createRouter, createWebHistory } from 'vue-router'
import VistaInicio from '@/vistas/VistaInicio.vue'
import VistaTareas from '@/vistas/VistaTareas.vue'
import VistaConocimiento from '@/vistas/VistaConocimiento.vue'
import VistaAjustes from '@/vistas/VistaAjustes.vue'
import VistaGruposEstados from '@/vistas/VistaGruposEstados.vue'
import VistaWorkflows from '@/vistas/VistaWorkflows.vue'

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
  ],
})

export default router
