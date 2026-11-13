# language: es
Característica: Workflow de las tareas
  Como persona usuaria de la aplicación
  Quiero elegir un workflow al crear o editar una tarea
  Para que sus pasos se añadan como subtareas y seguir su avance

  Antecedentes:
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta, Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido, Factura"

  Escenario: Una tarea creada con un workflow recibe sus pasos como subtareas pendientes
    Cuando creo la tarea "Venta" con el workflow "Ventas"
    Entonces la API responde 201 con la tarea "Venta", el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Los pasos se copian en el orden del workflow aunque se hayan reordenado
    Dado que reordeno los pasos del workflow "Ventas" como "Cierre, Contacto, Propuesta"
    Cuando creo la tarea "Venta" con el workflow "Ventas"
    Entonces al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Cierre, Contacto, Propuesta" pendientes

  Escenario: Una tarea creada sin workflow no recibe subtareas
    Cuando creo la tarea "Leer" sin workflow
    Entonces la API responde 201 con la tarea "Leer", sin workflow y sin subtareas
    Y al consultar las tareas "Leer" no tiene workflow ni subtareas

  Escenario: El tipo oportunidad por sí solo no añade subtareas
    Dado que existe el workflow "Workflow Oportunidades" con los pasos "Contacto, Cierre"
    Cuando creo una oportunidad "Venta" sin workflow
    Entonces la API responde 201 con la tarea "Venta", sin workflow y sin subtareas
    Y al consultar las tareas "Venta" no tiene workflow ni subtareas

  Escenario: Una oportunidad con un workflow recibe sus pasos
    Cuando creo una oportunidad "Venta" con el workflow "Ventas"
    Entonces al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Un workflow sin pasos se asigna sin añadir subtareas
    Dado que existe el workflow "Vacío" sin pasos
    Cuando creo la tarea "Leer" con el workflow "Vacío"
    Entonces al consultar las tareas "Leer" tiene el workflow "Vacío" y ninguna subtarea

  Escenario: Editar una tarea sin workflow para darle uno le añade sus pasos tras las subtareas que tenía
    Dado que existe la tarea "Venta" sin workflow
    Y la tarea "Venta" tiene la subtarea "Llamar" resuelta
    Cuando edito "Venta" con el workflow "Ventas"
    Entonces la API responde 200 con la tarea "Venta", el workflow "Ventas" y las subtareas "Llamar: resuelta; Contacto: pendiente; Propuesta: pendiente; Cierre: pendiente"
    Y al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Llamar: resuelta; Contacto: pendiente; Propuesta: pendiente; Cierre: pendiente"

  Escenario: Cambiar a otro workflow añade sus pasos y conserva los anteriores
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Y la subtarea "Contacto" de "Venta" está resuelta
    Cuando edito "Venta" con el workflow "Compras"
    Entonces al consultar las tareas "Venta" tiene el workflow "Compras" y las subtareas "Contacto: resuelta; Propuesta: pendiente; Cierre: pendiente; Pedido: pendiente; Factura: pendiente"

  Escenario: Editar con el mismo workflow no toca las subtareas
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Y la subtarea "Contacto" de "Venta" está resuelta
    Y borro la subtarea "Cierre" de "Venta"
    Cuando edito "Venta" con el workflow "Ventas"
    Entonces al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Contacto: resuelta; Propuesta: pendiente"

  Escenario: Quitar el workflow no toca las subtareas
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Cuando edito "Venta" sin workflow
    Entonces la API responde 200 con la tarea "Venta", sin workflow y las subtareas "Contacto: pendiente; Propuesta: pendiente; Cierre: pendiente"
    Y al consultar las tareas "Venta" no tiene workflow y tiene las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Editar sin indicar el workflow lo quita, como el grupo de estados
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Cuando edito "Venta" sin el campo workflow_id
    Entonces al consultar las tareas "Venta" no tiene workflow y tiene las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Cambiar el tipo de una tarea a oportunidad no le añade subtareas
    Dado que existe la tarea "Leer" sin workflow
    Cuando edito "Leer" como oportunidad sin workflow
    Entonces al consultar las tareas "Leer" no tiene workflow ni subtareas

  Esquema del escenario: Se rechaza un workflow que no existe
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Cuando intento <operacion> con un workflow que no existe
    Entonces la API responde 422 porque el workflow no existe
    Y al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y hay 1 tareas

    Ejemplos:
      | operacion           |
      | crear una tarea     |
      | editar "Venta"      |

  Esquema del escenario: Se rechaza un workflow_id que no es un entero
    Cuando intento crear una tarea con el workflow_id <valor>
    Entonces la API rechaza la operación por datos inválidos
    Y hay 0 tareas

    Ejemplos:
      | valor  |
      | "1"    |
      | 1.5    |
      | true   |

  Escenario: Eliminar un workflow deja sus tareas sin workflow y con sus subtareas
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Y que existe la tarea "Compra" con el workflow "Compras"
    Cuando elimino el workflow "Ventas"
    Entonces al consultar las tareas "Venta" no tiene workflow y tiene las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Compra" tiene el workflow "Compras" y las subtareas "Pedido, Factura" pendientes

  Escenario: Renombrar un workflow se refleja en sus tareas
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Cuando renombro el workflow "Ventas" a "Comercial"
    Entonces al consultar las tareas "Venta" tiene el workflow "Comercial" y las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Cambiar el workflow después no altera las subtareas de las tareas existentes
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Cuando añado el paso "Seguimiento" al workflow "Ventas"
    Y creo la tarea "Otra venta" con el workflow "Ventas"
    Entonces al consultar las tareas "Venta" tiene el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Otra venta" tiene el workflow "Ventas" y las subtareas "Contacto, Propuesta, Cierre, Seguimiento" pendientes
