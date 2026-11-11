# language: es
Característica: Subtareas creadas a partir del workflow de las oportunidades
  Como persona usuaria de la aplicación
  Quiero que cada oportunidad nueva reciba como subtareas los pasos del workflow
  Para seguir su avance como con cualquier otra subtarea

  Antecedentes:
    Dado que el workflow de las oportunidades tiene los pasos "Contacto, Propuesta, Cierre"

  Escenario: Una oportunidad nueva recibe los pasos del workflow como subtareas pendientes
    Cuando creo una tarea de tipo oportunidad "Venta"
    Entonces la API responde que "Venta" tiene las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Venta" tiene las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y la respuesta de la tarea no incluye pasos de la oportunidad

  Escenario: Una tarea sin tipo no recibe subtareas
    Cuando creo una tarea sin tipo "Leer"
    Entonces la API responde que "Leer" no tiene subtareas
    Y al consultar las tareas "Leer" no tiene subtareas

  Escenario: Una oportunidad con el workflow vacío no recibe subtareas
    Dado que el workflow de las oportunidades no tiene pasos
    Cuando creo una tarea de tipo oportunidad "Venta"
    Entonces la API responde que "Venta" no tiene subtareas

  Escenario: Cambiar el workflow después no altera las subtareas de las oportunidades existentes
    Dado que existe la oportunidad "Venta"
    Cuando cambio el workflow a los pasos "Cierre, Contacto, Seguimiento"
    Y creo una tarea de tipo oportunidad "Otra venta"
    Entonces al consultar las tareas "Venta" tiene las subtareas "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Otra venta" tiene las subtareas "Cierre, Contacto, Seguimiento" pendientes

  Escenario: Las subtareas del workflow se resuelven, editan y borran como cualquier subtarea
    Dado que existe la oportunidad "Venta"
    Cuando resuelvo la subtarea "Propuesta" de "Venta"
    Y renombro la subtarea "Cierre" de "Venta" a "Firma" con la persona "Ana" y la prioridad 2
    Y borro la subtarea "Contacto" de "Venta"
    Y añado la subtarea "Factura" a "Venta"
    Entonces al consultar las tareas "Venta" tiene las subtareas "Propuesta: -, -, resuelta; Firma: Ana, 2, pendiente; Factura: -, -, pendiente"

  Escenario: Editar una oportunidad que sigue siéndolo conserva sus subtareas
    Dado que existe la oportunidad "Venta"
    Y la subtarea "Contacto" de "Venta" está resuelta
    Cuando edito "Venta" como oportunidad con el código "OP-2"
    Entonces al consultar las tareas "Venta" tiene las subtareas "Contacto: -, -, resuelta; Propuesta: -, -, pendiente; Cierre: -, -, pendiente"

  Escenario: Una tarea que deja de ser oportunidad conserva sus subtareas
    Dado que existe la oportunidad "Venta"
    Cuando edito "Venta" sin tipo
    Entonces al consultar las tareas "Venta" tiene las subtareas "Contacto, Propuesta, Cierre" pendientes

  Escenario: Una tarea que pasa a ser oportunidad no recibe subtareas del workflow
    Dado que existe la tarea sin tipo "Leer"
    Cuando edito "Leer" como oportunidad con el código "OP-3"
    Entonces al consultar las tareas "Leer" no tiene subtareas

  Escenario: Ya no existe la ruta para marcar los pasos de una tarea
    Dado que existe la oportunidad "Venta"
    Cuando intento marcar como hecho el paso 1 de "Venta" por la ruta antigua
    Entonces la API responde que la ruta no existe
    Y al consultar las tareas "Venta" tiene las subtareas "Contacto, Propuesta, Cierre" pendientes
