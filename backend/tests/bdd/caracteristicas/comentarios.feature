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
    Y ningún comentario de "Mudanza" está editado

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

  Escenario: Editar un comentario cambia su texto, conserva su fecha de alta y lo marca como editado
    Dado que "Mudanza" tiene los comentarios "Llamar al casero; Pedir cajas"
    Cuando edito el comentario "Llamar al casero" de "Mudanza" con el texto "  Llamar al casero\nmañana  "
    Entonces la API responde 200 con el comentario editado "Llamar al casero\nmañana" con su fecha de alta
    Y los comentarios de "Mudanza" son "Llamar al casero\nmañana; Pedir cajas"
    Y en "Mudanza" solo está editado "Llamar al casero\nmañana", con su fecha de alta

  Escenario: Se admite editar un comentario con un texto de 500 caracteres
    Dado que "Mudanza" tiene los comentarios "Uno"
    Cuando edito el comentario "Uno" de "Mudanza" con un texto de 500 caracteres
    Entonces la API responde 200 con un comentario editado de 500 caracteres

  Esquema del escenario: Se rechaza editar un comentario con datos inválidos
    Dado que "Mudanza" tiene los comentarios "Uno"
    Cuando intento editar el comentario "Uno" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de "Mudanza" son "Uno"
    Y ningún comentario de "Mudanza" está editado

    Ejemplos:
      | cuerpo               |
      | {}                   |
      | {"texto": ""}        |
      | {"texto": " \\n\\t "} |
      | {"texto": null}      |
      | {"texto": 5}         |

  Escenario: Se rechaza editar un comentario con más de 500 caracteres
    Dado que "Mudanza" tiene los comentarios "Uno"
    Cuando intento editar el comentario "Uno" de "Mudanza" con un texto de 501 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de "Mudanza" son "Uno"
    Y ningún comentario de "Mudanza" está editado

  Escenario: Eliminar un comentario lo quita del histórico
    Dado que "Mudanza" tiene los comentarios "Uno; Dos; Tres"
    Cuando elimino el comentario "Dos" de "Mudanza"
    Entonces la API responde 204 sin contenido
    Y los comentarios de "Mudanza" son "Uno; Tres"

  Escenario: Se rechaza editar o eliminar un comentario de una tarea que no existe
    Dado que "Mudanza" tiene los comentarios "Uno"
    Cuando intento editar el comentario "Uno" de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Cuando intento eliminar el comentario "Uno" de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y los comentarios de "Mudanza" son "Uno"
    Y ningún comentario de "Mudanza" está editado

  Escenario: Se rechaza editar o eliminar un comentario que no existe
    Cuando intento editar el comentario con id 999999 de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene el comentario con id 999999
    Cuando intento eliminar el comentario con id 999999 de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene el comentario con id 999999

  Escenario: Se rechaza editar o eliminar el comentario de otra tarea
    Dado que existe la tarea "Viaje"
    Y que "Viaje" tiene los comentarios "Reservar"
    Cuando intento editar el comentario "Reservar" de "Viaje" a través de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene el comentario "Reservar" de "Viaje"
    Cuando intento eliminar el comentario "Reservar" de "Viaje" a través de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene el comentario "Reservar" de "Viaje"
    Y los comentarios de "Viaje" son "Reservar"
    Y ningún comentario de "Viaje" está editado
