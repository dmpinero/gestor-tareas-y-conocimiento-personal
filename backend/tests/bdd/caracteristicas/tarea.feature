# language: es
Característica: Creación, listado y edición de tareas
  Como persona usuaria de la aplicación
  Quiero crear y editar tareas con nombre, prioridad, descripción, fechas, etiquetas y personas asignadas
  Para tenerlas registradas y consultarlas en un listado

  Escenario: Alta correcta de una tarea con prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Preparar informe", prioridad 2, descripción "Informe trimestral" y fecha de creación "2026-11-09T10:30:00"
    Entonces la API responde que la tarea se ha creado con esos datos
    Y la tarea aparece en el listado de tareas

  Escenario: Alta correcta de una tarea sin prioridad
    Dado que no existe ninguna tarea
    Cuando creo una tarea con nombre "Leer", descripción "Un libro" y fecha de creación "2026-12-31T23:59:59" sin prioridad
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
      | fecha de creación  | ausente                   |
      | fecha de creación  | con zona horaria          |
      | fecha de creación  | en formato dd/mm/aaaa     |
      | fecha de vencimiento | en formato dd/mm/aaaa   |
      | etiquetas     | con un nombre vacío       |
      | etiquetas     | con un nombre de 51 caracteres |
      | asignados     | con un nombre solo de espacios |
      | asignados     | con un nombre de 101 caracteres |
      | tipo          | desconocido               |
      | código de la oportunidad | vacío          |
      | código de la oportunidad | solo espacios  |
      | código de la oportunidad | de 11 caracteres |
      | descripción de la oportunidad | de 201 caracteres |
      | observaciones de la oportunidad | de 5001 caracteres |

  Escenario: Edición correcta de una tarea
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando edito la tarea "Primera" con nombre "Primera editada", descripción "Nueva descripción" y fecha de creación "2027-01-15T08:05:09" sin prioridad
    Entonces la API responde que la tarea se ha actualizado con esos datos
    Y el listado muestra la tarea editada y "Segunda" sin cambios

  Escenario: Se rechaza editar una tarea que no existe
    Dado que no existe ninguna tarea
    Cuando intento editar la tarea con id 999999
    Entonces la API responde que la tarea no existe
    Y el listado de tareas sigue vacío

  Escenario: Se rechaza editar una tarea con datos inválidos
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando intento editar la tarea "Primera" sin fecha de creación
    Entonces la API rechaza la operación por datos inválidos
    Y el listado contiene "Primera" y "Segunda" sin cambios

  Escenario: Los catálogos de etiquetas y personas empiezan vacíos
    Dado que no existe ninguna tarea
    Entonces el catálogo de etiquetas contiene ""
    Y el catálogo de personas contiene ""

  Escenario: Alta de una tarea con etiquetas y personas nuevas
    Dado que no existe ninguna tarea
    Cuando creo una tarea con etiquetas "urgente, Casa, URGENTE" y asignados "Lucía, ana"
    Entonces la API responde que la tarea se ha creado con etiquetas "Casa, urgente" y asignados "ana, Lucía"
    Y la tarea aparece en el listado de tareas
    Y el catálogo de etiquetas contiene "Casa, urgente"
    Y el catálogo de personas contiene "ana, Lucía"

  Escenario: Alta de una tarea que reutiliza etiquetas y personas del catálogo
    Dado que existe una tarea con etiquetas "Urgente" y asignados "Ana López"
    Cuando creo una tarea con etiquetas "  urgente " y asignados "ANA LÓPEZ"
    Entonces la API responde que la tarea se ha creado con etiquetas "Urgente" y asignados "Ana López"
    Y el catálogo de etiquetas contiene "Urgente"
    Y el catálogo de personas contiene "Ana López"

  Escenario: La edición sustituye las etiquetas y personas de la tarea
    Dado que existe una tarea con etiquetas "casa, urgente" y asignados "Ana"
    Cuando edito esa tarea con etiquetas "trabajo, CASA" y asignados ""
    Entonces la API responde que la tarea se ha actualizado con etiquetas "casa, trabajo" y asignados ""
    Y el listado muestra solo esa tarea con etiquetas "casa, trabajo" y asignados ""
    Y el catálogo de etiquetas contiene "casa, trabajo, urgente"
    Y el catálogo de personas contiene "Ana"

  Escenario: Alta de una tarea con fecha de vencimiento
    Dado que no existe ninguna tarea
    Cuando creo una tarea con fecha de creación "2026-11-09T10:30:00" y fecha de vencimiento "2026-11-20T18:00:00"
    Entonces la API responde que la tarea se ha creado con esos datos
    Y la tarea aparece en el listado de tareas

  Escenario: Se rechaza una fecha de vencimiento anterior a la de creación
    Dado que no existe ninguna tarea
    Cuando creo una tarea con fecha de creación "2026-11-09T10:30:00" y fecha de vencimiento "2026-11-09T10:29:59"
    Entonces la API rechaza la operación con el mensaje "La fecha de vencimiento no puede ser anterior a la fecha de creación."
    Y el listado de tareas sigue vacío

  Escenario: Las tareas sin tipo no tienen datos de oportunidad
    Dado que existen las tareas "Primera" y "Segunda"
    Cuando consulto el listado de tareas
    Entonces ninguna tarea del listado tiene tipo ni oportunidad

  Escenario: Alta de una tarea de tipo oportunidad
    Dado que no existe ninguna tarea
    Cuando creo una tarea de tipo oportunidad con código "  OP-0001  ", descripción "Cliente nuevo" y observaciones "Llamar el lunes"
    Entonces la API responde que la tarea se ha creado con la oportunidad de código "OP-0001", descripción "Cliente nuevo" y observaciones "Llamar el lunes"
    Y la tarea aparece en el listado de tareas

  Escenario: Los textos opcionales vacíos de la oportunidad se guardan como nulos
    Dado que no existe ninguna tarea
    Cuando creo una tarea de tipo oportunidad con código "OP-1", descripción "   " y observaciones ""
    Entonces la API responde que la tarea se ha creado con la oportunidad de código "OP-1", descripción "" y observaciones ""
    Y la tarea aparece en el listado de tareas

  Escenario: Se rechaza una tarea de tipo oportunidad sin sus datos
    Dado que no existe ninguna tarea
    Cuando intento crear una tarea de tipo oportunidad sin sus datos
    Entonces la API rechaza la operación con el mensaje "Los datos de la oportunidad son obligatorios si el tipo es «oportunidad»."
    Y el listado de tareas sigue vacío

  Escenario: Se rechaza una tarea sin tipo con datos de oportunidad
    Dado que no existe ninguna tarea
    Cuando intento crear una tarea sin tipo con los datos de una oportunidad
    Entonces la API rechaza la operación con el mensaje "Los datos de la oportunidad solo se admiten si el tipo es «oportunidad»."
    Y el listado de tareas sigue vacío

  Escenario: La edición sustituye los datos de la oportunidad
    Dado que existe una tarea de tipo oportunidad con código "OP-1"
    Cuando edito esa tarea con la oportunidad de código "OP-2", descripción "Renovación" y observaciones ""
    Entonces la API responde que la tarea se ha actualizado con la oportunidad de código "OP-2", descripción "Renovación" y observaciones ""
    Y el listado muestra solo esa tarea

  Escenario: Quitar el tipo a una tarea borra sus datos de oportunidad
    Dado que existe una tarea de tipo oportunidad con código "OP-1"
    Cuando edito esa tarea sin tipo
    Entonces la API responde que la tarea se ha actualizado sin tipo ni oportunidad
    Y el listado muestra solo esa tarea

  Escenario: Se rechaza editar una tarea con datos de oportunidad pero sin tipo
    Dado que existe una tarea de tipo oportunidad con código "OP-1"
    Cuando intento editar esa tarea sin tipo pero con los datos de una oportunidad
    Entonces la API rechaza la operación con el mensaje "Los datos de la oportunidad solo se admiten si el tipo es «oportunidad»."
    Y el listado muestra la tarea de tipo oportunidad sin cambios
