<script setup lang="ts">
import { watch } from 'vue'

import { TIPOS_TAREA } from '@/api/tipos'
import SelectorEtiquetas from '@/componentes/compartido/SelectorEtiquetas.vue'
import SelectorFechaHora from '@/componentes/compartido/SelectorFechaHora.vue'
import { Button } from '@/componentes/ui/button'
import { Input } from '@/componentes/ui/input'
import { Label } from '@/componentes/ui/label'
import { Textarea } from '@/componentes/ui/textarea'
import type { ValoresFormularioTarea } from '@/lib/formularioTarea'
import { useTiendaGruposEstados } from '@/stores/gruposEstados'
import { useTiendaTareas } from '@/stores/tareas'
import { useTiendaWorkflows } from '@/stores/workflows'

// Campos de una tarea, compartidos por las ventanas modales de alta y de
// edición. Escribe directamente en `valores` (v-model); al enviar emite
// `guardar` y quien lo usa valida y guarda, y devuelve el fallo por `error`.
// "Cancelar" emite `cancelar`. El cuerpo desplaza y el pie con los botones
// queda fijo, para que en pantallas bajas se vea que hay más campos. `alta`
// indica que el formulario es el de crear una tarea. El slot `extra` añade
// campos tras el grupo de estados.
const valores = defineModel<ValoresFormularioTarea>('valores', { required: true })
const props = defineProps<{ error: string | null; alta?: boolean }>()
const emit = defineEmits<{ guardar: []; cancelar: [] }>()

const tienda = useTiendaTareas()
// Los grupos los carga quien usa el formulario. Un grupo sin estados no se
// puede asignar: la tarea no tendría estado en el que empezar.
const tiendaGrupos = useTiendaGruposEstados()
// Los workflows también los carga quien usa el formulario.
const tiendaWorkflows = useTiendaWorkflows()

const NOMBRE_WORKFLOW_OPORTUNIDADES = 'workflow oportunidades'

// En el alta, al elegir el tipo Oportunidad sin workflow, se propone el
// "Workflow Oportunidades" si existe. En la edición no: cambiar el workflow
// añade sus pasos como subtareas nuevas.
watch(
  () => valores.value.tipo,
  (tipo) => {
    if (!props.alta || tipo !== 'oportunidad' || valores.value.workflowId !== '') return
    const workflow = tiendaWorkflows.workflows.find(
      (candidato) => candidato.nombre.trim().toLowerCase() === NOMBRE_WORKFLOW_OPORTUNIDADES,
    )
    if (workflow) valores.value.workflowId = workflow.id
  },
)
</script>

<template>
  <form class="flex min-h-0 flex-1 flex-col" @submit.prevent="emit('guardar')">
    <div
      data-testid="cuerpo-formulario-tarea"
      class="flex min-h-0 flex-1 flex-col gap-3 overflow-y-scroll px-4 pb-4"
    >
      <!-- El color no es la única pista (WCAG 1.4.1): los obligatorios llevan
           además un asterisco y el atributo required. -->
      <p data-testid="leyenda-campos" class="text-muted-foreground text-xs">
        Los campos con * (borde rojo) son obligatorios; los de borde verde, opcionales.
      </p>
      <div class="campo-obligatorio flex flex-col gap-1.5">
        <Label for="tarea-nombre"
          >Nombre<span data-testid="marca-obligatorio" aria-hidden="true" class="text-destructive"
            >*</span
          ></Label
        >
        <Input
          id="tarea-nombre"
          v-model="valores.nombre"
          placeholder="Nombre"
          required
          maxlength="200"
        />
      </div>
      <div class="campo-opcional flex flex-col gap-1.5">
        <Label for="tarea-prioridad">Prioridad</Label>
        <Input
          id="tarea-prioridad"
          v-model="valores.prioridad"
          type="number"
          min="1"
          max="5"
          placeholder="Prioridad"
        />
      </div>
      <div class="campo-obligatorio flex flex-col gap-1.5">
        <Label for="tarea-descripcion"
          >Descripción<span
            data-testid="marca-obligatorio"
            aria-hidden="true"
            class="text-destructive"
            >*</span
          ></Label
        >
        <Textarea
          id="tarea-descripcion"
          v-model="valores.descripcion"
          placeholder="Descripción"
          required
          maxlength="500"
        />
      </div>
      <div class="campo-opcional">
        <SelectorEtiquetas
          id="etiquetas"
          v-model="valores.etiquetas"
          etiqueta="Etiquetas"
          :longitud-maxima="50"
          texto-nuevo='Crear etiqueta "{valor}"'
          :sugerencias="tienda.etiquetas"
        />
      </div>
      <div class="campo-opcional">
        <SelectorEtiquetas
          id="asignados"
          v-model="valores.asignados"
          etiqueta="Asignado a"
          :longitud-maxima="100"
          texto-nuevo='Añadir persona "{valor}"'
          :sugerencias="tienda.personas"
        />
      </div>
      <div class="campo-obligatorio flex flex-col gap-1.5">
        <Label for="fecha-creacion"
          >Fecha de creación<span
            data-testid="marca-obligatorio"
            aria-hidden="true"
            class="text-destructive"
            >*</span
          ></Label
        >
        <SelectorFechaHora
          id="fecha-creacion"
          v-model="valores.fechaCreacion"
          etiqueta="Fecha de creación"
          required
        />
      </div>
      <div class="campo-opcional flex flex-col gap-1.5">
        <Label for="fecha-vencimiento">Fecha de vencimiento</Label>
        <SelectorFechaHora
          id="fecha-vencimiento"
          v-model="valores.fechaVencimiento"
          etiqueta="Fecha de vencimiento"
          anulable
        />
      </div>
      <div class="campo-opcional flex flex-col gap-1.5">
        <Label for="tarea-tipo">Tipo de tarea</Label>
        <select
          id="tarea-tipo"
          v-model="valores.tipo"
          class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
        >
          <option value="">Sin tipo</option>
          <option v-for="tipo in TIPOS_TAREA" :key="tipo.valor" :value="tipo.valor">
            {{ tipo.etiqueta }}
          </option>
        </select>
      </div>
      <div class="campo-opcional flex flex-col gap-1.5">
        <Label for="tarea-grupo-estados">Grupo de estados</Label>
        <select
          id="tarea-grupo-estados"
          v-model="valores.grupoEstadosId"
          class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
        >
          <option value="">Sin grupo</option>
          <option
            v-for="grupo in tiendaGrupos.grupos"
            :key="grupo.id"
            :value="grupo.id"
            :disabled="grupo.estados.length === 0"
          >
            {{ grupo.estados.length === 0 ? `${grupo.nombre} (sin estados)` : grupo.nombre }}
          </option>
        </select>
      </div>
      <!-- Campos que añade quien usa el formulario (p. ej. el detalle, que también
           edita si está completada y el estado del grupo). -->
      <slot name="extra" />
      <div class="campo-opcional flex flex-col gap-1.5">
        <Label for="tarea-workflow">Workflow</Label>
        <select
          id="tarea-workflow"
          v-model="valores.workflowId"
          class="border-input dark:bg-input/30 bg-background focus-visible:border-ring focus-visible:ring-ring/50 h-9 w-full rounded-md border px-3 py-1 text-base shadow-xs outline-none focus-visible:ring-[3px] md:text-sm"
        >
          <option value="">Sin workflow</option>
          <option
            v-for="workflow in tiendaWorkflows.workflows"
            :key="workflow.id"
            :value="workflow.id"
          >
            {{ workflow.nombre }}
          </option>
        </select>
      </div>
      <fieldset
        v-if="valores.tipo === 'oportunidad'"
        class="flex flex-col gap-3 rounded-md border p-3"
      >
        <legend class="px-1 text-sm font-medium">Oportunidad</legend>
        <div class="campo-obligatorio flex flex-col gap-1.5">
          <Label for="oportunidad-codigo"
            >Código de la oportunidad<span
              data-testid="marca-obligatorio"
              aria-hidden="true"
              class="text-destructive"
              >*</span
            ></Label
          >
          <Input
            id="oportunidad-codigo"
            v-model="valores.oportunidad.codigo"
            required
            maxlength="10"
          />
        </div>
        <div class="campo-opcional flex flex-col gap-1.5">
          <Label for="oportunidad-descripcion">Descripción de la oportunidad</Label>
          <Input
            id="oportunidad-descripcion"
            v-model="valores.oportunidad.descripcion"
            maxlength="200"
          />
        </div>
        <div class="campo-opcional flex flex-col gap-1.5">
          <Label for="oportunidad-observaciones">Observaciones</Label>
          <Textarea
            id="oportunidad-observaciones"
            v-model="valores.oportunidad.observaciones"
            maxlength="5000"
          />
        </div>
      </fieldset>
    </div>

    <div class="bg-background flex flex-col gap-2 border-t px-4 py-3">
      <p v-if="props.error" class="text-sm text-destructive" role="alert">
        {{ props.error }}
      </p>
      <div class="flex gap-2">
        <Button type="submit" variant="success">Guardar</Button>
        <Button type="button" variant="destructive" @click="emit('cancelar')">Cancelar</Button>
      </div>
    </div>
  </form>
</template>

<style scoped>
/* Borde de los campos según sean obligatorios u opcionales. Solo los controles de
   texto y las listas; los botones de icono (calendario, borrar fecha) no cambian.
   Tonos con contraste de al menos 3:1 con el fondo (WCAG 1.4.11). */
.campo-obligatorio :deep(:is(input, textarea, select)) {
  border-color: oklch(0.577 0.245 27.325); /* rojo 600 */
}
.campo-opcional :deep(:is(input, textarea, select)) {
  border-color: oklch(0.527 0.154 150.069); /* verde 700 */
}
:global(.dark) .campo-obligatorio :deep(:is(input, textarea, select)) {
  border-color: oklch(0.704 0.191 22.216); /* rojo 400 */
}
:global(.dark) .campo-opcional :deep(:is(input, textarea, select)) {
  border-color: oklch(0.792 0.209 151.711); /* verde 400 */
}
</style>
