# language: es
Característica: Comentarios de las subtareas
  Como persona usuaria de la aplicación
  Quiero añadir, editar y borrar comentarios en cada subtarea
  Para llevar un histórico de lo que va ocurriendo con ella

  Antecedentes:
    Dado que existe la tarea "Mudanza" con las subtareas "Cajas; Camión"

  Escenario: Una subtarea nueva no tiene comentarios
    Entonces los comentarios de la subtarea "Cajas" de "Mudanza" son ""
    Y al consultar las tareas la subtarea "Cajas" de "Mudanza" tiene 0 comentarios

  Escenario: Añadir un comentario guarda el texto recortado y la fecha del servidor en UTC
    Cuando comento "  Pedir 20 cajas\ngrandes  " en la subtarea "Cajas" de "Mudanza"
    Entonces la API responde 201 con el comentario "Pedir 20 cajas\ngrandes" fechado ahora en UTC
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son "Pedir 20 cajas\ngrandes"
    Y al consultar las tareas la subtarea "Cajas" de "Mudanza" tiene 1 comentarios
    Y al consultar las tareas la subtarea "Camión" de "Mudanza" tiene 0 comentarios
    Y los comentarios de "Mudanza" son ""

  Escenario: Los comentarios de una subtarea se devuelven en orden cronológico
    Cuando comento "Uno" en la subtarea "Cajas" de "Mudanza"
    Y comento "Dos" en la subtarea "Cajas" de "Mudanza"
    Y comento "Otra" en la subtarea "Camión" de "Mudanza"
    Y comento "Tres" en la subtarea "Cajas" de "Mudanza"
    Entonces los comentarios de la subtarea "Cajas" de "Mudanza" son "Uno; Dos; Tres"
    Y los comentarios de la subtarea "Camión" de "Mudanza" son "Otra"
    Y al consultar las tareas la subtarea "Cajas" de "Mudanza" tiene 3 comentarios

  Escenario: Se admite un comentario de 500 caracteres
    Cuando comento un texto de 500 caracteres en la subtarea "Cajas" de "Mudanza"
    Entonces la API responde 201 con un comentario de 500 caracteres

  Esquema del escenario: Se rechaza un comentario de subtarea con datos inválidos
    Cuando intento comentar en la subtarea "Cajas" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son ""

    Ejemplos:
      | cuerpo                        |
      | {}                            |
      | {"texto": ""}                 |
      | {"texto": " \\n\\t "}          |
      | {"texto": null}               |
      | {"texto": 5}                  |
      | {"texto": "<501 caracteres>"} |

  Escenario: Editar un comentario de subtarea cambia su texto, conserva su fecha de alta y lo marca como editado
    Dado que la subtarea "Cajas" de "Mudanza" tiene los comentarios "Pedir cajas; Comprar cinta"
    Cuando edito el comentario "Pedir cajas" de la subtarea "Cajas" de "Mudanza" con el texto "  Pedir 30 cajas  "
    Entonces la API responde 200 con el comentario editado "Pedir 30 cajas" con su fecha de alta
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son "Pedir 30 cajas; Comprar cinta"
    Y en la subtarea "Cajas" de "Mudanza" solo está editado "Pedir 30 cajas"

  Esquema del escenario: Se rechaza editar un comentario de subtarea con datos inválidos
    Dado que la subtarea "Cajas" de "Mudanza" tiene los comentarios "Uno"
    Cuando intento editar el comentario "Uno" de la subtarea "Cajas" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son "Uno"
    Y en la subtarea "Cajas" de "Mudanza" ningún comentario está editado

    Ejemplos:
      | cuerpo                        |
      | {}                            |
      | {"texto": " "}                |
      | {"texto": "<501 caracteres>"} |

  Escenario: Eliminar un comentario de subtarea lo quita del histórico
    Dado que la subtarea "Cajas" de "Mudanza" tiene los comentarios "Uno; Dos; Tres"
    Cuando elimino el comentario "Dos" de la subtarea "Cajas" de "Mudanza"
    Entonces la API responde 204 sin contenido
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son "Uno; Tres"
    Y al consultar las tareas la subtarea "Cajas" de "Mudanza" tiene 2 comentarios

  Escenario: Borrar la subtarea borra sus comentarios
    Dado que la subtarea "Cajas" de "Mudanza" tiene los comentarios "Uno; Dos"
    Y que la subtarea "Camión" de "Mudanza" tiene los comentarios "Alquilar"
    Cuando borro la subtarea "Cajas" de "Mudanza"
    Entonces en la base de datos solo quedan los comentarios de subtarea "Alquilar"

  Esquema del escenario: Se rechaza operar con los comentarios de una subtarea de una tarea que no existe
    Dado que la subtarea "Cajas" de "Mudanza" tiene los comentarios "Uno"
    Cuando intento <accion> el comentario "Uno" de la subtarea "Cajas" a través de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y los comentarios de la subtarea "Cajas" de "Mudanza" son "Uno"
    Y en la subtarea "Cajas" de "Mudanza" ningún comentario está editado

    Ejemplos:
      | accion   |
      | listar   |
      | comentar |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza operar con los comentarios de una subtarea que no existe
    Cuando intento <accion> los comentarios de la subtarea con id 999999 de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea con id 999999

    Ejemplos:
      | accion   |
      | listar   |
      | comentar |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza operar con los comentarios de la subtarea de otra tarea
    Dado que existe la tarea "Viaje" con las subtareas "Billetes"
    Y que la subtarea "Billetes" de "Viaje" tiene los comentarios "Comprar"
    Cuando intento <accion> el comentario "Comprar" de la subtarea "Billetes" de "Viaje" a través de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea "Billetes" de "Viaje"
    Y los comentarios de la subtarea "Billetes" de "Viaje" son "Comprar"
    Y en la subtarea "Billetes" de "Viaje" ningún comentario está editado

    Ejemplos:
      | accion   |
      | listar   |
      | comentar |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza editar o eliminar un comentario que no existe en la subtarea
    Cuando intento <accion> el comentario con id 999999 de la subtarea "Cajas" de "Mudanza"
    Entonces la API responde que la subtarea "Cajas" de "Mudanza" no tiene el comentario con id 999999

    Ejemplos:
      | accion   |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza editar o eliminar el comentario de otra subtarea
    Dado que la subtarea "Camión" de "Mudanza" tiene los comentarios "Alquilar"
    Cuando intento <accion> el comentario "Alquilar" de "Camión" a través de la subtarea "Cajas" de "Mudanza"
    Entonces la API responde que la subtarea "Cajas" de "Mudanza" no tiene el comentario "Alquilar" de "Camión"
    Y los comentarios de la subtarea "Camión" de "Mudanza" son "Alquilar"
    Y en la subtarea "Camión" de "Mudanza" ningún comentario está editado

    Ejemplos:
      | accion   |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza editar o eliminar el comentario de la tarea por la ruta de la subtarea
    Dado que "Mudanza" tiene el comentario de tarea "De la tarea"
    Cuando intento <accion> el comentario de tarea "De la tarea" a través de la subtarea "Cajas" de "Mudanza"
    Entonces la API responde que la subtarea "Cajas" de "Mudanza" no tiene el comentario de tarea "De la tarea"
    Y los comentarios de "Mudanza" son "De la tarea"

    Ejemplos:
      | accion   |
      | editar   |
      | eliminar |
