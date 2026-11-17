# language: es
Característica: Contador de vencimiento congelado de las tareas terminadas
  Como persona usuaria de la aplicación
  Quiero que una tarea completada o en estado DONE tenga parado el contador de "Vence en"
  Para que muestre el tiempo que faltaba cuando la terminé, y vuelva a contar si la reabro

  Antecedentes:
    Dado que hay un grupo "Flujo" con los estados "TODO, DOING, DONE"
    Y que existe la tarea "Informe" en el grupo "Flujo" con vencimiento "2026-12-01T10:00:00"

  Escenario: Una tarea nueva y pendiente no está congelada
    Entonces la tarea "Informe" no está congelada

  Escenario: Marcar la tarea como completada la congela en ese instante
    Cuando marco la tarea "Informe" como completada
    Entonces la API responde 200 con la tarea congelada en este instante
    Y la tarea "Informe" se guarda congelada en este instante

  Escenario: Mover la tarea al estado DONE la congela en ese instante
    Cuando muevo la tarea "Informe" al estado "DONE"
    Entonces la API responde 200 con la tarea congelada en este instante
    Y la tarea "Informe" se guarda congelada en este instante

  Escenario: El estado DONE se reconoce sin distinguir mayúsculas y en cualquier grupo
    Dado que hay un grupo "Otro" con los estados "Abierta, done"
    Y que existe la tarea "Carta" en el grupo "Otro" con vencimiento "2026-12-01T10:00:00"
    Cuando muevo la tarea "Carta" al estado "done"
    Entonces la API responde 200 con la tarea congelada en este instante

  Escenario: Mover la tarea a un estado que no es DONE no la congela
    Cuando muevo la tarea "Informe" al estado "DOING"
    Entonces la API responde 200 con la tarea sin congelar
    Y la tarea "Informe" no está congelada

  Escenario: Pasar de completada a DONE conserva el instante en que se congeló
    Dado que la tarea "Informe" está completada y congelada desde "2026-11-01T08:00:00Z"
    Cuando muevo la tarea "Informe" al estado "DONE"
    Y desmarco la tarea "Informe" como completada
    Entonces la API responde 200 con la tarea congelada desde "2026-11-01T08:00:00Z"
    Y la tarea "Informe" se guarda congelada desde "2026-11-01T08:00:00Z"

  Escenario: Pasar de DONE a completada conserva el instante en que se congeló
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Cuando marco la tarea "Informe" como completada
    Y muevo la tarea "Informe" al estado "TODO"
    Entonces la API responde 200 con la tarea congelada desde "2026-11-01T08:00:00Z"
    Y la tarea "Informe" se guarda congelada desde "2026-11-01T08:00:00Z"

  Escenario: Volver a marcar como completada una tarea ya completada no cambia el instante
    Dado que la tarea "Informe" está completada y congelada desde "2026-11-01T08:00:00Z"
    Cuando marco la tarea "Informe" como completada
    Entonces la API responde 200 con la tarea congelada desde "2026-11-01T08:00:00Z"

  Escenario: Desmarcar como completada una tarea que no está en DONE reanuda el contador
    Dado que la tarea "Informe" está completada y congelada desde "2026-11-01T08:00:00Z"
    Cuando desmarco la tarea "Informe" como completada
    Entonces la API responde 200 con la tarea sin congelar
    Y la tarea "Informe" no está congelada

  Escenario: Sacar la tarea de DONE reanuda el contador
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Cuando muevo la tarea "Informe" al estado "DOING"
    Entonces la API responde 200 con la tarea sin congelar
    Y la tarea "Informe" no está congelada

  Escenario: Cambiar el vencimiento de una tarea congelada conserva el instante
    Dado que la tarea "Informe" está completada y congelada desde "2026-11-01T08:00:00Z"
    Cuando edito la tarea "Informe" con vencimiento "2026-12-20T18:30:00" y el grupo "Flujo"
    Entonces la API responde 200 con la tarea congelada desde "2026-11-01T08:00:00Z"
    Y la respuesta tiene el vencimiento "2026-12-20T18:30:00"
    Y la tarea "Informe" se guarda congelada desde "2026-11-01T08:00:00Z"

  Escenario: Quitar el grupo a una tarea en DONE que no está completada reanuda el contador
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Cuando edito la tarea "Informe" con vencimiento "2026-12-01T10:00:00" y sin grupo
    Entonces la API responde 200 con la tarea sin congelar
    Y la tarea "Informe" no está congelada

  Escenario: Editar una tarea pendiente sin cambiar su estado no la congela
    Cuando edito la tarea "Informe" con vencimiento "2026-12-20T18:30:00" y el grupo "Flujo"
    Entonces la API responde 200 con la tarea sin congelar
    Y la respuesta tiene el vencimiento "2026-12-20T18:30:00"

  Escenario: Asignar un grupo cuyo primer estado es DONE congela la tarea
    Dado que hay un grupo "Cerrado" con los estados "DONE, TODO"
    Cuando edito la tarea "Informe" con vencimiento "2026-12-01T10:00:00" y el grupo "Cerrado"
    Entonces la API responde 200 con la tarea congelada en este instante
    Y la tarea "Informe" se guarda congelada en este instante

  Escenario: Crear una tarea en un grupo cuyo primer estado es DONE la crea congelada
    Dado que hay un grupo "Cerrado" con los estados "DONE, TODO"
    Cuando creo la tarea "Acta" en el grupo "Cerrado" con vencimiento "2026-12-01T10:00:00"
    Entonces la API responde 201 con la tarea congelada en este instante
    Y la tarea "Acta" se guarda congelada en este instante

  Escenario: Crear una tarea en un grupo cuyo primer estado no es DONE la crea sin congelar
    Cuando creo la tarea "Acta" en el grupo "Flujo" con vencimiento "2026-12-01T10:00:00"
    Entonces la API responde 201 con la tarea sin congelar
    Y la tarea "Acta" no está congelada

  Escenario: Renombrar un estado a DONE congela sus tareas
    Dado que hay un grupo "Otro" con los estados "Abierta, Lista"
    Y que existe la tarea "Carta" en el grupo "Otro" con vencimiento "2026-12-01T10:00:00"
    Cuando cambio el nombre del estado "Abierta" del grupo "Otro" a "Done"
    Entonces la tarea "Carta" se guarda congelada en este instante
    Y la tarea "Informe" no está congelada

  Escenario: Renombrar el estado DONE reanuda el contador de sus tareas no completadas
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Y que existe la tarea "Acta" en el grupo "Flujo" con vencimiento "2026-12-01T10:00:00"
    Y que la tarea "Acta" está en DONE, completada y congelada desde "2026-11-02T09:00:00Z"
    Cuando cambio el nombre del estado "DONE" del grupo "Flujo" a "Cerrada"
    Entonces la tarea "Informe" no está congelada
    Y la tarea "Acta" se guarda congelada desde "2026-11-02T09:00:00Z"

  Escenario: Eliminar un estado moviendo sus tareas a DONE las congela
    Dado que muevo la tarea "Informe" al estado "DOING"
    Cuando borro el estado "DOING" del grupo "Flujo" pasando sus tareas a "DONE"
    Entonces la tarea "Informe" se guarda congelada en este instante

  Escenario: Eliminar el estado DONE moviendo sus tareas a otro reanuda el contador
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Cuando borro el estado "DONE" del grupo "Flujo" pasando sus tareas a "TODO"
    Entonces la tarea "Informe" no está congelada

  Escenario: Eliminar el grupo reanuda el contador de sus tareas en DONE no completadas
    Dado que la tarea "Informe" está en DONE y congelada desde "2026-11-01T08:00:00Z"
    Y que existe la tarea "Acta" en el grupo "Flujo" con vencimiento "2026-12-01T10:00:00"
    Y que la tarea "Acta" está en DONE, completada y congelada desde "2026-11-02T09:00:00Z"
    Cuando borro el grupo "Flujo"
    Entonces la tarea "Informe" no está congelada
    Y la tarea "Acta" se guarda congelada desde "2026-11-02T09:00:00Z"

  Escenario: Una tarea sin vencimiento también guarda el instante, sin más efecto
    Dado que existe la tarea "Nota" en el grupo "Flujo" sin vencimiento
    Cuando marco la tarea "Nota" como completada
    Entonces la API responde 200 con la tarea congelada en este instante
    Y la respuesta no tiene vencimiento

  Escenario: El listado de tareas incluye el instante en que se congeló
    Dado que la tarea "Informe" está completada y congelada desde "2026-11-01T08:00:00Z"
    Entonces el listado muestra la tarea "Informe" congelada desde "2026-11-01T08:00:00Z"
