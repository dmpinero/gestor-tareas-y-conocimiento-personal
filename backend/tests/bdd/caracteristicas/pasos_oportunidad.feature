# language: es
Característica: Pasos de las tareas de tipo oportunidad
  Como persona usuaria de la aplicación
  Quiero que cada oportunidad nueva tenga los pasos del workflow de las oportunidades
  Para seguir su avance marcando cada paso como hecho o pendiente

  Antecedentes:
    Dado que el workflow de las oportunidades tiene los pasos "Contacto, Propuesta, Cierre"

  Escenario: Una oportunidad nueva recibe una copia de los pasos del workflow
    Cuando creo una tarea de tipo oportunidad "Venta"
    Entonces la API responde que "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes

  Escenario: Una tarea sin tipo no recibe pasos
    Cuando creo una tarea sin tipo "Leer"
    Entonces la API responde que "Leer" no tiene pasos
    Y al consultar las tareas "Leer" no tiene pasos

  Escenario: Cambiar el workflow después no altera los pasos de las oportunidades existentes
    Dado que existe la oportunidad "Venta"
    Cuando cambio el workflow a los pasos "Cierre, Contacto, Seguimiento"
    Y creo una tarea de tipo oportunidad "Otra venta"
    Entonces al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Otra venta" tiene los pasos "Cierre, Contacto, Seguimiento" pendientes

  Escenario: Marcar un paso como hecho y volver a dejarlo pendiente
    Dado que existe la oportunidad "Venta"
    Cuando marco el paso "Propuesta" de "Venta" como hecho
    Entonces la API responde con "Venta" y sus pasos "Contacto: pendiente, Propuesta: hecho, Cierre: pendiente"
    Y al consultar las tareas "Venta" tiene los pasos "Contacto: pendiente, Propuesta: hecho, Cierre: pendiente"
    Cuando marco el paso "Propuesta" de "Venta" como pendiente
    Entonces la API responde con "Venta" y sus pasos "Contacto: pendiente, Propuesta: pendiente, Cierre: pendiente"
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes

  Escenario: Editar una oportunidad que sigue siéndolo conserva sus pasos y su avance
    Dado que existe la oportunidad "Venta"
    Y el paso "Contacto" de "Venta" está hecho
    Cuando edito "Venta" como oportunidad con el código "OP-2"
    Entonces la API responde con "Venta" y sus pasos "Contacto: hecho, Propuesta: pendiente, Cierre: pendiente"
    Y al consultar las tareas "Venta" tiene los pasos "Contacto: hecho, Propuesta: pendiente, Cierre: pendiente"

  Escenario: Una tarea que deja de ser oportunidad pierde sus pasos
    Dado que existe la oportunidad "Venta"
    Cuando edito "Venta" sin tipo
    Entonces la API responde que "Venta" no tiene pasos
    Y al consultar las tareas "Venta" no tiene pasos

  Escenario: Una tarea que pasa a ser oportunidad no recibe pasos
    Dado que existe la tarea sin tipo "Leer"
    Cuando edito "Leer" como oportunidad con el código "OP-3"
    Entonces la API responde que "Leer" no tiene pasos
    Y al consultar las tareas "Leer" no tiene pasos

  Esquema del escenario: Se rechaza un estado del paso que no es un booleano
    Dado que existe la oportunidad "Venta"
    Cuando intento cambiar el paso "Contacto" de "Venta" con el cuerpo <cuerpo>
    Entonces la API rechaza el cambio del paso por datos inválidos
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes

    Ejemplos:
      | cuerpo             |
      | {"hecho": "true"}  |
      | {"hecho": 1}       |
      | {"hecho": null}    |
      | {}                 |

  Escenario: Se rechaza cambiar un paso de una tarea que no existe
    Dado que existe la oportunidad "Venta"
    Cuando intento marcar como hecho el paso "Contacto" de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes

  Escenario: Se rechaza cambiar un paso que no existe
    Dado que existe la oportunidad "Venta"
    Cuando intento marcar como hecho el paso con id 999999 de "Venta"
    Entonces la API responde que "Venta" no tiene el paso con id 999999
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes

  Escenario: Se rechaza cambiar el paso de otra tarea
    Dado que existe la oportunidad "Venta"
    Y que existe la oportunidad "Otra venta"
    Cuando intento marcar como hecho el paso "Contacto" de "Otra venta" a través de "Venta"
    Entonces la API responde que "Venta" no tiene el paso "Contacto" de "Otra venta"
    Y al consultar las tareas "Venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes
    Y al consultar las tareas "Otra venta" tiene los pasos "Contacto, Propuesta, Cierre" pendientes
