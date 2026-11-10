# language: es
Característica: Pasos del workflow de las oportunidades
  Como persona usuaria de la aplicación
  Quiero definir los pasos estándar que se realizan en orden en cada oportunidad
  Para tener el workflow de las oportunidades ordenado y numerado

  Escenario: Sin pasos, el workflow está vacío
    Dado que el workflow no tiene pasos
    Cuando consulto los pasos del workflow
    Entonces la API devuelve una lista de pasos vacía

  Escenario: Cada paso nuevo es continuación del anterior
    Dado que el workflow tiene los pasos "Contacto, Propuesta"
    Cuando añado el paso "Cierre"
    Entonces la API responde que el paso "Cierre" se ha creado con el número 3
    Y el workflow guarda los pasos "Contacto, Propuesta, Cierre"

  Escenario: El nombre del paso se guarda sin los espacios de los extremos
    Dado que el workflow no tiene pasos
    Cuando añado el paso "  Primer contacto  "
    Entonces la API responde que el paso "Primer contacto" se ha creado con el número 1
    Y el workflow guarda los pasos "Primer contacto"

  Esquema del escenario: Se rechaza un paso con un nombre inválido
    Dado que el workflow tiene los pasos "Contacto"
    Cuando intento añadir un paso con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow guarda los pasos "Contacto"

    Ejemplos:
      | nombre             |
      | vacío              |
      | solo de espacios   |
      | con espacio duro   |
      | de 51 caracteres   |
      | ausente            |
      | que no es texto    |

  Escenario: Se admite un nombre de 50 caracteres
    Dado que el workflow no tiene pasos
    Cuando añado un paso con un nombre de 50 caracteres
    Entonces la API responde que el paso se ha creado con ese nombre y el número 1

  Escenario: Renombrar un paso no cambia su número
    Dado que el workflow tiene los pasos "Contacto, Propuesta"
    Cuando renombro el paso "Propuesta" a "  Oferta "
    Entonces la API responde con el paso "Oferta" y el número 2
    Y el workflow guarda los pasos "Contacto, Oferta"

  Esquema del escenario: Se rechaza renombrar un paso con un nombre inválido
    Dado que el workflow tiene los pasos "Contacto"
    Cuando intento renombrar el paso "Contacto" con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow guarda los pasos "Contacto"

    Ejemplos:
      | nombre             |
      | vacío              |
      | solo de espacios   |
      | de 51 caracteres   |

  Esquema del escenario: Eliminar un paso renumera los siguientes
    Dado que el workflow tiene los pasos "Contacto, Propuesta, Negociación, Cierre"
    Cuando elimino el paso "<eliminado>"
    Entonces la API responde que el paso se ha eliminado
    Y el workflow guarda los pasos "<quedan>"

    Ejemplos:
      | eliminado   | quedan                           |
      | Contacto    | Propuesta, Negociación, Cierre   |
      | Negociación | Contacto, Propuesta, Cierre      |
      | Cierre      | Contacto, Propuesta, Negociación |

  Escenario: Reordenar los pasos recalcula sus números
    Dado que el workflow tiene los pasos "Contacto, Propuesta, Negociación, Cierre"
    Cuando reordeno los pasos como "Negociación, Contacto, Cierre, Propuesta"
    Entonces la API devuelve los pasos "Negociación, Contacto, Cierre, Propuesta"
    Y el workflow guarda los pasos "Negociación, Contacto, Cierre, Propuesta"

  Esquema del escenario: Se rechaza un orden que no incluye cada paso exactamente una vez
    Dado que el workflow tiene los pasos "Contacto, Propuesta, Cierre"
    Cuando intento reordenar los pasos con un orden <orden>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow guarda los pasos "Contacto, Propuesta, Cierre"

    Ejemplos:
      | orden                        |
      | con un paso repetido         |
      | al que le falta un paso      |
      | con un paso que no existe    |
      | vacío                        |
      | con ids que no son enteros   |
      | ausente                      |

  Esquema del escenario: Un paso que no existe responde 404
    Dado que el workflow tiene los pasos "Contacto"
    Cuando intento <operacion> el paso con un id que no existe
    Entonces la API responde que el paso no existe
    Y el workflow guarda los pasos "Contacto"

    Ejemplos:
      | operacion  |
      | renombrar  |
      | eliminar   |
