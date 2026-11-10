import { createRouter, createWebHistory } from 'vue-router'
import VistaInicio from '@/vistas/VistaInicio.vue'
import VistaTareas from '@/vistas/VistaTareas.vue'
import VistaConocimiento from '@/vistas/VistaConocimiento.vue'
import VistaAjustes from '@/vistas/VistaAjustes.vue'
import VistaWorkflowOportunidades from '@/vistas/VistaWorkflowOportunidades.vue'

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
      path: '/ajustes/workflow-oportunidades',
      name: 'workflow-oportunidades',
      component: VistaWorkflowOportunidades,
    },
  ],
})

export default router
