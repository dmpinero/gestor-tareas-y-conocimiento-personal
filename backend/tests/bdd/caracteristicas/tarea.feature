# language: es
Característica: Creación, listado y edición de tareas
  Como persona usuaria de la aplicación
  Quiero crear y editar tareas con nombre, prioridad, descripción y fecha y hora
  Para tenerlas registradas y consultarlas en un listado

  Escenario: Alta correcta de una tarea con prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Preparar informe", prioridad 2, descripción "Informe trimestral" y fecha y hora "2026-11-09T10:30:00"
    Entonces la API responde que la tarea se ha creado con esos datos
    Y la tarea aparece en el listado de tareas

  Escenario: Alta correcta de una tarea sin prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Leer", descripción "Un libro" y fecha y hora "2026-12-31T23:59:59" sin prioridad
    Entonces la API responde que la tarea se ha creado con esos datos
    Y la tarea aparece en el listado de tareas

  Escenario: El listado devuelve las tareas en el orden en que se crearon
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando consulto el listado de tareas
    Entonces el listado contiene "Primera" y "Segunda" en ese orden

  Esquema del escenario: Se rechaza una tarea con datos inválidos
    Dado que no existe ninguna tarea
    Cuando intento crear una tarea con <campo> <valor>
    Entonces la API rechaza la operación por datos inválidos
    Y el listado de tareas sigue vacío

    Ejemplos:
      | campo         | valor                     |
      | nombre        | vacío                     |
      | nombre        | solo espacios             |
      | nombre        | de 201 caracteres         |
      | descripción   | vacía                     |
      | descripción   | de 501 caracteres         |
      | prioridad     | 0                         |
      | prioridad     | 6                         |
      | fecha y hora  | ausente                   |
      | fecha y hora  | con zona horaria          |
      | fecha y hora  | en formato dd/mm/aaaa     |

  Escenario: Edición correcta de una tarea
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando edito la tarea "Primera" con nombre "Primera editada", descripción "Nueva descripción" y fecha y hora "2027-01-15T08:05:09" sin prioridad
    Entonces la API responde que la tarea se ha actualizado con esos datos
    Y el listado muestra la tarea editada y "Segunda" sin cambios

  Escenario: Se rechaza editar una tarea que no existe
    Dado que no existe ninguna tarea
    Cuando intento editar la tarea con id 999999
    Entonces la API responde que la tarea no existe
    Y el listado de tareas sigue vacío

  Escenario: Se rechaza editar una tarea con datos inválidos
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando intento editar la tarea "Primera" sin fecha y hora
    Entonces la API rechaza la operación por datos inválidos
    Y el listado contiene "Primera" y "Segunda" sin cambios
