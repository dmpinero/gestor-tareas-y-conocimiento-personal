# language: es
Característica: Borrar tareas
  Como persona usuaria de la aplicación
  Quiero eliminar las tareas que ya no necesito
  Para que dejen de aparecer, junto con sus subtareas y comentarios

  Antecedentes:
    Dado que existe la oportunidad "Venta" con la etiqueta "Clientes" y la persona "Ana"
    Y que "Venta" tiene la subtarea "Llamar" asignada a "Luis" con el comentario "Sin respuesta"
    Y que "Venta" tiene el comentario "Primer contacto"
    Y que existe la tarea "Leer" con la subtarea "Capítulo 1" y el comentario "Empezado"

  Escenario: Borrar una tarea responde 204 sin contenido y la quita del listado
    Cuando borro la tarea "Venta"
    Entonces la API responde 204 sin contenido
    Y al consultar las tareas solo aparece "Leer"

  Escenario: Borrar una tarea borra sus subtareas, sus comentarios y los de sus subtareas
    Cuando borro la tarea "Venta"
    Entonces en la base de datos no queda nada de "Venta"
    Y "Leer" conserva sus subtareas y sus comentarios

  Escenario: Borrar una tarea conserva los catálogos de etiquetas y personas
    Cuando borro la tarea "Venta"
    Entonces el catálogo de etiquetas sigue teniendo "Clientes"
    Y el catálogo de personas sigue teniendo "Ana, Luis"

  Escenario: Se rechaza borrar una tarea que no existe
    Cuando intento borrar la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y al consultar las tareas aparecen "Venta, Leer"

  Escenario: Se rechaza borrar dos veces la misma tarea
    Dado que he borrado la tarea "Venta"
    Cuando intento borrar otra vez la tarea "Venta"
    Entonces la API responde que no existe la tarea "Venta"
    Y al consultar las tareas solo aparece "Leer"
