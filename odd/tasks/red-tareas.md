# Vista de red de tareas ("nube")
Objetivo: ver de forma gráfica cómo se relacionan las tareas entre sí (relacionadas, etiquetas, personas, subestado, oportunidad). Rama: feat/red-tareas. Entrega: single-pr (solo frontend, como las funcionalidades anteriores).
Tests: frontend vitest + vue-tsc + eslint/prettier + playwright (e2e en pila aislada 33731/8970/4970).

## Specs
- S1 "quiero tener una opción para ver las tareas en formato nube, a través de un componente gráfico que me permita saber cómo están relacionadas todas las tareas entre sí, sirviéndonos de todas las etiquetas, etc. para verlo de forma gráfica".
- S2 Tipo de red elegido: "Nodos propios (Recomendado)": cada etiqueta, persona, subestado u oportunidad es un nodo propio y las tareas se unen a él; las tareas relacionadas se unen directamente entre sí.
- S3 (supuesto) Cuarta vista en Tareas, «Ver como red» (junto a lista, tablero y calendario), recordada como las demás; usa las tareas ya filtradas por la búsqueda y los filtros.
- S4 (supuesto) Casillas «Relacionadas», «Etiquetas», «Personas», «Subestados», «Oportunidades» para elegir qué uniones se muestran (todas marcadas por defecto; se recuerdan en el navegador). Un nodo de etiqueta/persona/subestado/oportunidad solo aparece si une a 2 o más tareas visibles (uno con una sola tarea no relaciona nada).
- S5 (supuesto) Tareas: círculo con el color de su prioridad (mismos colores que la app), nombre debajo (recortado); completadas atenuadas. Nodos propios con forma/color por tipo y su nombre; leyenda.
- S6 (supuesto) Pasar el ratón o enfocar un nodo resalta sus vecinos y atenúa el resto. Clic (o Enter) en una tarea abre su detalle. Clic en un nodo propio fija el resaltado de sus tareas (otro clic lo quita).
- S7 (supuesto) Zoom con botones (+, −, ajustar) y con la rueda; arrastrar el fondo desplaza la vista.
- S8 (supuesto) Accesible: cada nodo es enfocable con nombre accesible (p. ej. «Tarea Informe: 3 conexiones»), AA de contraste en claro y oscuro, funciona en móvil. Sin tareas: «Ninguna tarea coincide con los filtros.»; con tareas pero sin uniones visibles: «Estas tareas no tienen nada en común con las uniones elegidas.»
- S9 (supuesto) Disposición con d3-force (dependencia nueva `d3-force`), calculada de forma determinista (misma entrada → mismas posiciones) y dibujada en SVG con Vue.

## Tasks
- T1 S2,S4 `lib/redTareas.ts`: construir nodos y aristas a partir de las tareas y las uniones elegidas (función pura) + tests — inline
- T2 S9 `lib/disposicionRed.ts`: posiciones con d3-force, deterministas + tests — inline
- T3 S3,S5-S8 `RedTareas.vue` + integración en `VistaTareas.vue` + tests — inline
- T4 S1-S8 e2e (incluye axe claro/oscuro y móvil), README — inline

## Log
- L1 (2026-11-26) "quiero tener una opción para ver las tareas en formato nube, a través de un componente gráfico que me permita saber cómo están relacionadas todas las tareas entre sí, sirviéndonos de todas las etiquetas, etc. para verlo de forma gráfica. No sé si me entiendes"
- L2 (2026-11-26) Pregunta tipo de red → "Nodos propios (Recomendado)".
- L3 Librería: d3-force en lugar de Cytoscape (mucho más ligera, solo calcula posiciones; el dibujo en SVG con Vue mantiene tokens, modo oscuro y nodos accesibles).
