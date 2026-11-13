# language: es
Característica: Comentarios de los pasos de los workflows
  Como persona usuaria de la aplicación
  Quiero escribir comentarios en los pasos de los workflows, igual que en las tareas
  Para que se trasladen a las subtareas de las tareas de ese workflow y pueda
  modificarlos después de forma independiente en la tarea

  Antecedentes:
    Dado que el workflow "Ventas" tiene los pasos "Contacto; Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido"

  Escenario: Un paso nuevo no tiene comentarios
    Entonces los comentarios del paso "Contacto" de "Ventas" son ""
    Y al consultar los workflows el paso "Contacto" de "Ventas" tiene 0 comentarios

  Escenario: Añadir un comentario a un paso guarda el texto recortado y la fecha del servidor en UTC
    Cuando comento "  Llamar antes\nde las 10  " en el paso "Contacto" de "Ventas"
    Entonces la API responde 201 con el comentario "Llamar antes\nde las 10" fechado ahora en UTC
    Y los comentarios del paso "Contacto" de "Ventas" son "Llamar antes\nde las 10"
    Y al consultar los workflows el paso "Contacto" de "Ventas" tiene 1 comentarios
    Y al consultar los workflows el paso "Cierre" de "Ventas" tiene 0 comentarios

  Escenario: Los comentarios de un paso se devuelven en orden cronológico
    Cuando comento "Uno" en el paso "Contacto" de "Ventas"
    Y comento "Otro" en el paso "Cierre" de "Ventas"
    Y comento "Dos" en el paso "Contacto" de "Ventas"
    Entonces los comentarios del paso "Contacto" de "Ventas" son "Uno; Dos"
    Y los comentarios del paso "Cierre" de "Ventas" son "Otro"

  Esquema del escenario: Se rechaza un comentario de paso con datos inválidos
    Cuando intento comentar en el paso "Contacto" de "Ventas" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios del paso "Contacto" de "Ventas" son ""

    Ejemplos:
      | cuerpo                        |
      | {}                            |
      | {"texto": ""}                 |
      | {"texto": " \\n\\t "}          |
      | {"texto": null}               |
      | {"texto": 5}                  |
      | {"texto": "<501 caracteres>"} |

  Escenario: Se admite un comentario de paso de 500 caracteres
    Cuando comento un texto de 500 caracteres en el paso "Contacto" de "Ventas"
    Entonces la API responde 201 con un comentario de 500 caracteres

  Escenario: Editar un comentario de paso cambia su texto, conserva su fecha de alta y lo marca como editado
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Llamar; Enviar correo"
    Cuando edito el comentario "Llamar" del paso "Contacto" de "Ventas" con el texto "  Llamar dos veces  "
    Entonces la API responde 200 con el comentario editado "Llamar dos veces" con su fecha de alta
    Y los comentarios del paso "Contacto" de "Ventas" son "Llamar dos veces; Enviar correo"

  Escenario: Se rechaza editar un comentario de paso con un texto inválido
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Llamar"
    Cuando intento editar el comentario "Llamar" del paso "Contacto" de "Ventas" con el cuerpo {"texto": " "}
    Entonces la API rechaza la petición por datos inválidos
    Y los comentarios del paso "Contacto" de "Ventas" son "Llamar"

  Escenario: Eliminar un comentario de paso lo quita del histórico
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Uno; Dos; Tres"
    Cuando elimino el comentario "Dos" del paso "Contacto" de "Ventas"
    Entonces la API responde 204 sin contenido
    Y los comentarios del paso "Contacto" de "Ventas" son "Uno; Tres"
    Y al consultar los workflows el paso "Contacto" de "Ventas" tiene 2 comentarios

  Escenario: Borrar un paso borra sus comentarios
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Uno; Dos"
    Y que el paso "Cierre" de "Ventas" tiene los comentarios "Firmar"
    Cuando borro el paso "Contacto" de "Ventas"
    Entonces en la base de datos solo quedan los comentarios de paso "Firmar"

  Esquema del escenario: Se rechaza operar con los comentarios de un paso de un workflow que no existe
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Uno"
    Cuando intento <accion> el comentario "Uno" del paso "Contacto" de "Ventas" a través del workflow con id 999999
    Entonces la API responde 404 con "No existe el workflow con id 999999"
    Y los comentarios del paso "Contacto" de "Ventas" son "Uno"

    Ejemplos:
      | accion   |
      | listar   |
      | comentar |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza operar con los comentarios del paso de otro workflow
    Dado que el paso "Pedido" de "Compras" tiene los comentarios "Pedir"
    Cuando intento <accion> el comentario "Pedir" del paso "Pedido" de "Compras" a través de "Ventas"
    Entonces la API responde que "Ventas" no tiene el paso "Pedido" de "Compras"
    Y los comentarios del paso "Pedido" de "Compras" son "Pedir"

    Ejemplos:
      | accion   |
      | listar   |
      | comentar |
      | editar   |
      | eliminar |

  Esquema del escenario: Se rechaza editar o eliminar el comentario de otro paso
    Dado que el paso "Cierre" de "Ventas" tiene los comentarios "Firmar"
    Cuando intento <accion> el comentario "Firmar" del paso "Cierre" de "Ventas" a través del paso "Contacto"
    Entonces la API responde que el paso "Contacto" de "Ventas" no tiene el comentario "Firmar" del paso "Cierre"
    Y los comentarios del paso "Cierre" de "Ventas" son "Firmar"

    Ejemplos:
      | accion   |
      | editar   |
      | eliminar |

  Escenario: Una tarea creada con un workflow recibe en cada subtarea los comentarios de su paso
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Llamar; Enviar\ncorreo"
    Y que el paso "Cierre" de "Ventas" tiene los comentarios "Firmar"
    Cuando creo la tarea "Venta" con el workflow "Ventas"
    Entonces la subtarea "Contacto" de "Venta" tiene los comentarios copiados "Llamar; Enviar\ncorreo" fechados ahora y sin editar
    Y la subtarea "Cierre" de "Venta" tiene los comentarios copiados "Firmar" fechados ahora y sin editar
    Y al consultar las tareas las subtareas de "Venta" tienen "2; 1" comentarios

  Escenario: Los comentarios con formato de un paso se copian tal cual a la subtarea
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "<p><strong>Llamar</strong> <em>antes</em><script>alert(1)</script></p>; <ul><li>a&amp;b</li></ul>"
    Entonces los comentarios del paso "Contacto" de "Ventas" son "<p><strong>Llamar</strong> <em>antes</em></p>; <ul><li>a&amp;b</li></ul>"
    Cuando creo la tarea "Venta" con el workflow "Ventas"
    Entonces la subtarea "Contacto" de "Venta" tiene los comentarios copiados "<p><strong>Llamar</strong> <em>antes</em></p>; <ul><li>a&amp;b</li></ul>" fechados ahora y sin editar

  Escenario: Editar una tarea para darle otro workflow copia los comentarios de sus pasos
    Dado que el paso "Pedido" de "Compras" tiene los comentarios "Pedir presupuesto"
    Y que existe la tarea "Venta" con el workflow "Ventas"
    Cuando edito "Venta" con el workflow "Compras"
    Entonces la subtarea "Pedido" de "Venta" tiene los comentarios copiados "Pedir presupuesto" fechados ahora y sin editar
    Y los comentarios de la subtarea "Contacto" de "Venta" son ""

  Esquema del escenario: Editar con el mismo workflow o sin workflow no copia comentarios
    Dado que existe la tarea "Venta" con el workflow "Ventas"
    Y que el paso "Contacto" de "Ventas" tiene los comentarios "Llamar"
    Cuando edito "Venta" <workflow>
    Entonces al consultar las tareas las subtareas de "Venta" tienen "0; 0" comentarios
    Y en la base de datos solo quedan los comentarios de subtarea ""

    Ejemplos:
      | workflow                  |
      | con el workflow "Ventas"  |
      | sin workflow              |

  Escenario: Los comentarios copiados y los del paso se modifican de forma independiente
    Dado que el paso "Contacto" de "Ventas" tiene los comentarios "Uno; Dos"
    Y que existe la tarea "Venta" con el workflow "Ventas"
    Cuando edito el comentario "Uno" del paso "Contacto" de "Ventas" con el texto "Uno en el paso"
    Y elimino el comentario "Dos" del paso "Contacto" de "Ventas"
    Entonces los comentarios de la subtarea "Contacto" de "Venta" son "Uno; Dos"
    Cuando edito el comentario "Uno" de la subtarea "Contacto" de "Venta" con el texto "Uno en la tarea"
    Y elimino el comentario "Dos" de la subtarea "Contacto" de "Venta"
    Entonces los comentarios de la subtarea "Contacto" de "Venta" son "Uno en la tarea"
    Y los comentarios del paso "Contacto" de "Ventas" son "Uno en el paso"
