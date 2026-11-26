# Mejoras visuales de las vistas de tareas
Objetivo: aplicar las 17 mejoras propuestas en la revisión visual de lista, tablero y calendario.
Rama: feat/mejoras-visuales-vistas (apilada sobre feat/pulsar-todas-las-pildoras). Entrega: single-pr. Tests: vitest + playwright.

## Specs
- S1 Lista: "El nombre se aplasta" → insignias debajo del nombre y ancho mínimo de columna.
- S2 Lista: descripción como máximo 2 líneas, completa al pasar el ratón.
- S3 Lista: Estado no cortado → columna Nombre fija al desplazar en horizontal.
- S4 Lista: fecha de creación "16 nov", fecha completa al pasar el ratón.
- S5 Lista: subestado sin partir línea, truncado con "…".
- S6 Lista móvil: tarjetas en pantallas estrechas.
- S7 Tablero: avatares superpuestos con borde del color de la tarjeta.
- S8 Tablero: completadas sin "Vencida hace…", solo fecha con check y tarjeta atenuada.
- S9 Tablero: iconos de acción atenuados, resaltados al pasar el ratón o con foco; visibles en táctil.
- S10 Tablero: barra de colores junto a "Tarjetas por fila" con leyenda/tooltip.
- S11 Tablero: subestado distinguible de las etiquetas.
- S12 Calendario: interruptor "Ocultar completadas".
- S13 Calendario: semanas vacías más bajas.
- S14 Calendario: "N tareas sin fecha de vencimiento" pulsable, abre la ventana de tareas relacionadas.
- S15 Calendario: borde izquierdo de color por estado/prioridad.
- S16 Calendario móvil: navegación con flechas solo icono + "Hoy".
- S17 General: en móvil la píldora "Trabajando en" conserva el nombre de la tarea.

## Tasks
- T1 S1-S6 lista — inline — hecho 1404123 (RED 7/9 → GREEN; S3 por columna fija tras medir 355 px de desborde)
- T2 S7-S11 tablero — inline — hecho cd8cff9 (RED 6/6 → GREEN)
- T3 S12-S16 calendario — inline — hecho (RED 5/6 → GREEN)
- T4 S17 barra superior — inline — hecho (RED 2/2 → GREEN)

## Log
- L1 (2026-11-26) "Revisa cómo se visuslizan las tareas en las distintas vistas y proponme mejoras visuales" → propuesta de 17 puntos; usuario: "implementa todos".
- L2 S3: reordenar columnas rompía el orden del Excel exportado; se optó por fijar la columna Nombre (franja con sombra interior: los bordes colapsados no se desplazan).
- L3 S9: acciones ocultas (opacity-0) en vez de atenuadas para no bajar el contraste por debajo de AA; visibles en táctil, con foco o con la tarea en foco/hibernada.
