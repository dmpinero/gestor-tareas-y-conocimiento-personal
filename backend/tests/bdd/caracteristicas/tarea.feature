# language: es
Característica: Creación y listado de tareas
  Como persona usuaria de la aplicación
  Quiero crear tareas con nombre, prioridad y descripción
  Para tenerlas registradas y consultarlas en un listado

  Escenario: Alta correcta de una tarea con prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Preparar informe", prioridad 2 y descripción "Informe trimestral"
    Entonces la API responde que la tarea se ha creado con esos datos
    Y la tarea aparece en el listado de tareas

  Escenario: Alta correcta de una tarea sin prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Leer" y descripción "Un libro" sin prioridad
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
      | campo       | valor                     |
      | nombre      | vacío                     |
      | nombre      | solo espacios             |
      | nombre      | de 201 caracteres         |
      | descripción | vacía                     |
      | descripción | de 501 caracteres         |
      | prioridad   | 0                         |
      | prioridad   | 6                         |
