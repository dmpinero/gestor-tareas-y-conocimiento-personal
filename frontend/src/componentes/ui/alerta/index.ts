import { type VariantProps, cva } from 'class-variance-authority'

export { default as Alerta } from './Alerta.vue'

// Recuadro que destaca un mensaje sobre el contenido. "aviso" usa ámbar: texto
// 900 sobre fondo 50 (y 100 sobre 950 en oscuro), por encima de 4,5:1.
export const variantesAlerta = cva(
  "flex items-start gap-3 rounded-lg border px-4 py-3 text-sm [&>svg]:mt-0.5 [&>svg]:shrink-0 [&>svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: 'bg-card text-card-foreground',
        aviso:
          'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export type VariantesAlerta = VariantProps<typeof variantesAlerta>
