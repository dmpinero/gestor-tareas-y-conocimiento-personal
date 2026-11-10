# language: es
Característica: Histórico de comentarios de una tarea
  Como persona usuaria de la aplicación
  Quiero añadir comentarios de texto a una tarea
  Para llevar un histórico cronológico de lo que va ocurriendo

  Antecedentes:
    Dado que existe la tarea "Mudanza"

  Escenario: Una tarea nueva no tiene comentarios
    Entonces los comentarios de "Mudanza" son ""

  Escenario: Añadir un comentario guarda el texto recortado y la fecha del servidor en UTC
    Cuando comento "  Llamar al casero  " en "Mudanza"
    Entonces la API responde 201 con el comentario "Llamar al casero" fechado ahora en UTC
    Y los comentarios de "Mudanza" son "Llamar al casero"

  Escenario: Los saltos de línea del interior del texto se conservan
    Cuando comento "\nPrimera línea\nSegunda línea\n" en "Mudanza"
    Entonces la API responde 201 con el comentario "Primera línea\nSegunda línea" fechado ahora en UTC
    Y los comentarios de "Mudanza" son "Primera línea\nSegunda línea"

  Escenario: Los comentarios se devuelven en orden cronológico y no aparecen en la tarea
    Cuando comento "Uno" en "Mudanza"
    Y comento "Dos" en "Mudanza"
    Y comento "Tres" en "Mudanza"
    Entonces los comentarios de "Mudanza" son "Uno; Dos; Tres"
    Y al consultar las tareas "Mudanza" no incluye comentarios

  Escenario: Cada tarea tiene sus propios comentarios
    Dado que existe la tarea "Viaje"
    Cuando comento "De la mudanza" en "Mudanza"
    Y comento "Del viaje" en "Viaje"
    Entonces los comentarios de "Mudanza" son "De la mudanza"
    Y los comentarios de "Viaje" son "Del viaje"

  Escenario: Se admite un comentario de 500 caracteres
    Cuando comento un texto de 500 caracteres en "Mudanza"
    Entonces la API responde 201 con un comentario de 500 caracteres

  Esquema del escenario: Se rechaza un comentario con datos inválidos
    Cuando intento comentar en "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de "Mudanza" son ""

    Ejemplos:
      | cuerpo               |
      | {}                   |
      | {"texto": ""}        |
      | {"texto": " \\n\\t "} |
      | {"texto": null}      |
      | {"texto": 5}         |

  Escenario: Se rechaza un comentario de más de 500 caracteres
    Cuando intento comentar en "Mudanza" un texto de 501 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de "Mudanza" son ""

  Escenario: Se rechaza comentar o listar los comentarios de una tarea que no existe
    Cuando intento comentar "Hola" en la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Cuando consulto los comentarios de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
