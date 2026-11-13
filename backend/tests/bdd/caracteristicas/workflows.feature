# language: es
Característica: Workflows con nombre y sus pasos
  Como persona usuaria de la aplicación
  Quiero definir varios workflows con nombre, cada uno con sus pasos en orden
  Para añadir a cada tarea los pasos del workflow que le corresponda

  Escenario: Los workflows se listan por nombre sin distinguir mayúsculas
    Dado que existen los workflows "ventas, Alta, compras"
    Cuando consulto los workflows
    Entonces la API devuelve los workflows "Alta, compras, ventas"

  Escenario: Un workflow nuevo no tiene pasos y su nombre se guarda sin los espacios de los extremos
    Cuando creo el workflow "  Ventas  "
    Entonces la API responde que el workflow "Ventas" se ha creado sin pasos
    Y se guardan los workflows "Ventas"

  Esquema del escenario: Se rechaza un workflow con un nombre inválido
    Cuando intento crear un workflow con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y no se guarda ningún workflow

    Ejemplos:
      | nombre             |
      | vacío              |
      | solo de espacios   |
      | con espacio duro   |
      | de 51 caracteres   |
      | ausente            |
      | que no es texto    |

  Escenario: Se admite un nombre de workflow de 50 caracteres con tildes
    Cuando creo un workflow con un nombre de 50 caracteres con tildes
    Entonces la API responde que el workflow se ha creado con ese nombre

  Esquema del escenario: No puede haber dos workflows con el mismo nombre sin distinguir mayúsculas
    Dado que existen los workflows "Ventas, Compras"
    Cuando <operacion> "<nombre>"
    Entonces la API responde que ya existe un workflow llamado "<nombre>"
    Y se guardan los workflows "Compras, Ventas"

    Ejemplos:
      | operacion                        | nombre |
      | creo el workflow                 | VENTAS |
      | renombro el workflow "Compras" a | ventas |

  Escenario: Renombrar un workflow conserva sus pasos
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta"
    Cuando renombro el workflow "Ventas" a " Comercial "
    Entonces la API responde con el workflow "Comercial" y los pasos "Contacto, Propuesta"
    Y el workflow "Comercial" guarda los pasos "Contacto, Propuesta"

  Escenario: Renombrar un workflow con su mismo nombre en otras mayúsculas
    Dado que existen los workflows "Ventas"
    Cuando renombro el workflow "Ventas" a "VENTAS"
    Entonces la API responde con el workflow "VENTAS" sin pasos

  Escenario: Eliminar un workflow borra sus pasos y no toca los de otro
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta"
    Y que el workflow "Compras" tiene los pasos "Pedido"
    Cuando elimino el workflow "Ventas"
    Entonces la API responde que se ha eliminado
    Y se guardan los workflows "Compras"
    Y el workflow "Compras" guarda los pasos "Pedido"
    Y no queda ningún paso del workflow eliminado

  Esquema del escenario: Un workflow que no existe responde 404
    Dado que existen los workflows "Ventas"
    Cuando intento <operacion> un workflow que no existe
    Entonces la API responde que el workflow no existe
    Y se guardan los workflows "Ventas"

    Ejemplos:
      | operacion                 |
      | renombrar                 |
      | eliminar                  |
      | añadir un paso a          |
      | reordenar los pasos de    |

  Escenario: Cada paso nuevo es continuación del anterior en su workflow
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta"
    Y que el workflow "Compras" tiene los pasos "Pedido"
    Cuando añado el paso "Cierre" al workflow "Ventas"
    Entonces la API responde 201 con el workflow "Ventas" y los pasos "Contacto, Propuesta, Cierre"
    Y el workflow "Ventas" guarda los pasos "Contacto, Propuesta, Cierre"
    Y el workflow "Compras" guarda los pasos "Pedido"

  Escenario: El nombre del paso se guarda sin los espacios de los extremos
    Dado que existen los workflows "Ventas"
    Cuando añado el paso "  Primer contacto  " al workflow "Ventas"
    Entonces la API responde 201 con el workflow "Ventas" y los pasos "Primer contacto"
    Y el workflow "Ventas" guarda los pasos "Primer contacto"

  Esquema del escenario: Se rechaza un paso con un nombre inválido
    Dado que el workflow "Ventas" tiene los pasos "Contacto"
    Cuando intento añadir al workflow "Ventas" un paso con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow "Ventas" guarda los pasos "Contacto"

    Ejemplos:
      | nombre             |
      | vacío              |
      | solo de espacios   |
      | con espacio duro   |
      | de 51 caracteres   |
      | ausente            |
      | que no es texto    |

  Escenario: Se admite un paso de 50 caracteres
    Dado que existen los workflows "Ventas"
    Cuando añado al workflow "Ventas" un paso con un nombre de 50 caracteres
    Entonces la API responde 201 con el workflow "Ventas" y un paso de 50 caracteres

  Escenario: Renombrar un paso no cambia su número
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta"
    Cuando renombro el paso "Propuesta" del workflow "Ventas" a "  Oferta "
    Entonces la API responde con el workflow "Ventas" y los pasos "Contacto, Oferta"
    Y el workflow "Ventas" guarda los pasos "Contacto, Oferta"

  Esquema del escenario: Se rechaza renombrar un paso con un nombre inválido
    Dado que el workflow "Ventas" tiene los pasos "Contacto"
    Cuando intento renombrar el paso "Contacto" del workflow "Ventas" con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow "Ventas" guarda los pasos "Contacto"

    Ejemplos:
      | nombre             |
      | vacío              |
      | solo de espacios   |
      | de 51 caracteres   |

  Esquema del escenario: Eliminar un paso renumera los siguientes de su workflow
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta, Negociación, Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido, Factura"
    Cuando elimino el paso "<eliminado>" del workflow "Ventas"
    Entonces la API responde con el workflow "Ventas" y los pasos "<quedan>"
    Y el workflow "Ventas" guarda los pasos "<quedan>"
    Y el workflow "Compras" guarda los pasos "Pedido, Factura"

    Ejemplos:
      | eliminado   | quedan                           |
      | Contacto    | Propuesta, Negociación, Cierre   |
      | Negociación | Contacto, Propuesta, Cierre      |
      | Cierre      | Contacto, Propuesta, Negociación |

  Escenario: Reordenar los pasos recalcula sus números solo en su workflow
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta, Negociación, Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido, Factura"
    Cuando reordeno los pasos del workflow "Ventas" como "Negociación, Contacto, Cierre, Propuesta"
    Entonces la API responde con el workflow "Ventas" y los pasos "Negociación, Contacto, Cierre, Propuesta"
    Y el workflow "Ventas" guarda los pasos "Negociación, Contacto, Cierre, Propuesta"
    Y el workflow "Compras" guarda los pasos "Pedido, Factura"

  Escenario: Reordenar un workflow sin pasos con un orden vacío
    Dado que existen los workflows "Ventas"
    Cuando reordeno los pasos del workflow "Ventas" con un orden vacío
    Entonces la API responde con el workflow "Ventas" sin pasos

  Esquema del escenario: Se rechaza un orden que no incluye cada paso del workflow exactamente una vez
    Dado que el workflow "Ventas" tiene los pasos "Contacto, Propuesta, Cierre"
    Y que el workflow "Compras" tiene los pasos "Pedido"
    Cuando intento reordenar los pasos del workflow "Ventas" con un orden <orden>
    Entonces la API rechaza la operación por datos inválidos
    Y el workflow "Ventas" guarda los pasos "Contacto, Propuesta, Cierre"
    Y el workflow "Compras" guarda los pasos "Pedido"

    Ejemplos:
      | orden                          |
      | con un paso repetido           |
      | al que le falta un paso        |
      | con un paso que no existe      |
      | con un paso de otro workflow   |
      | vacío                          |
      | con ids que no son enteros     |
      | ausente                        |

  Esquema del escenario: Un paso que no es del workflow responde 404
    Dado que el workflow "Ventas" tiene los pasos "Contacto"
    Y que el workflow "Compras" tiene los pasos "Pedido"
    Cuando intento <operacion> el paso "<paso>" en el workflow "Ventas"
    Entonces la API responde que el paso "<paso>" no existe en el workflow "Ventas"
    Y el workflow "Ventas" guarda los pasos "Contacto"
    Y el workflow "Compras" guarda los pasos "Pedido"

    Ejemplos:
      | operacion  | paso       |
      | renombrar  | inexistente |
      | eliminar   | inexistente |
      | renombrar  | Pedido     |
      | eliminar   | Pedido     |

  Escenario: Ya no existen las rutas del workflow de las oportunidades
    Cuando consulto la ruta antigua de los pasos del workflow de las oportunidades
    Entonces la API responde que la ruta no existe
