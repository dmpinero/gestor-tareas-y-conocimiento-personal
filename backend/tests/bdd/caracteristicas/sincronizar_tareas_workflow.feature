# language: es
Característica: Sincronizar las tareas abiertas con su workflow
  Como persona usuaria de la aplicación
  Quiero poner al día las tareas ya creadas después de editar su workflow
  Para que tengan los pasos nuevos y los nombres actuales sin perder lo que ya hice

  Antecedentes:
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta, Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido, Factura"
    Y que existe la tarea "Venta" con el workflow "Ventas"

  Escenario: Consultar los cambios pendientes no modifica nada
    Dado que añado el paso "Seguimiento" al workflow "Ventas"
    Y que renombro el paso "Contacto" del workflow "Ventas" a "Primer contacto"
    Cuando consulto los cambios pendientes del workflow "Ventas"
    Entonces la API responde 200 con los cambios "Venta: añadir Seguimiento; renombrar Contacto > Primer contacto"
    Y "Venta" tiene las subtareas "Contacto, Propuesta, Cierre"

  Escenario: Sin cambios pendientes la consulta devuelve una lista vacía
    Cuando consulto los cambios pendientes del workflow "Ventas"
    Entonces la API responde 200 sin cambios

  Escenario: Sincronizar añade los pasos nuevos en su posición, con sus comentarios, y renombra las subtareas
    Dado que añado el paso "Seguimiento" al workflow "Ventas"
    Y que el paso "Seguimiento" de "Ventas" tiene el comentario "<p>Llamar a los 15 días</p>"
    Y que reordeno los pasos del workflow "Ventas" como "Contacto, Seguimiento, Propuesta, Cierre"
    Y que renombro el paso "Contacto" del workflow "Ventas" a "Primer contacto"
    Y la subtarea "Contacto" de "Venta" está resuelta
    Cuando sincronizo las tareas del workflow "Ventas"
    Entonces la API responde 200 con los cambios "Venta: añadir Seguimiento; renombrar Contacto > Primer contacto"
    Y "Venta" tiene las subtareas "Primer contacto: resuelta; Seguimiento: pendiente; Propuesta: pendiente; Cierre: pendiente"
    Y las subtareas "Primer contacto, Seguimiento, Propuesta, Cierre" de "Venta" están vinculadas a sus pasos del workflow "Ventas"
    Y la subtarea "Seguimiento" de "Venta" no tiene persona ni prioridad y tiene los comentarios copiados "<p>Llamar a los 15 días</p>"

  Escenario: Los pasos borrados, las tareas completadas, las de otros workflows y las subtareas añadidas a mano no cambian
    Dado que la tarea "Venta" tiene la subtarea "Llamar" añadida a mano
    Y que existe la tarea "Hecha" con el workflow "Ventas"
    Y que la tarea "Hecha" está completada
    Y que existe la tarea "Compra" con el workflow "Compras"
    Y que elimino el paso "Cierre" del workflow "Ventas"
    Y que añado el paso "Seguimiento" al workflow "Ventas"
    Cuando sincronizo las tareas del workflow "Ventas"
    Entonces la API responde 200 con los cambios "Venta: añadir Seguimiento"
    Y "Venta" tiene las subtareas "Contacto, Propuesta, Seguimiento, Cierre, Llamar"
    Y la subtarea "Cierre" de "Venta" no está vinculada a ningún paso
    Y la subtarea "Llamar" de "Venta" no está vinculada a ningún paso
    Y "Hecha" tiene las subtareas "Contacto, Propuesta, Cierre"
    Y "Compra" tiene las subtareas "Pedido, Factura"

  Escenario: Sincronizar dos veces no cambia nada la segunda vez
    Dado que añado el paso "Seguimiento" al workflow "Ventas"
    Y que renombro el paso "Propuesta" del workflow "Ventas" a "Oferta"
    Y que sincronizo las tareas del workflow "Ventas"
    Cuando sincronizo las tareas del workflow "Ventas"
    Entonces la API responde 200 sin cambios
    Y "Venta" tiene las subtareas "Contacto, Oferta, Cierre, Seguimiento"
    Y al consultar los cambios pendientes del workflow "Ventas" no hay ninguno

  Esquema del escenario: Un workflow que no existe responde 404
    Cuando <operacion> de un workflow que no existe
    Entonces la API responde 404 porque el workflow no existe
    Y "Venta" tiene las subtareas "Contacto, Propuesta, Cierre"

    Ejemplos:
      | operacion                    |
      | consulto los cambios         |
      | sincronizo las tareas        |
