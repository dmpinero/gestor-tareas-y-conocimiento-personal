# language: es
Característica: Subtareas de una tarea
  Como persona usuaria de la aplicación
  Quiero crear subtareas dentro de una tarea, con persona asignada y prioridad opcionales
  Para dividirla en partes y marcar cada una como resuelta

  Antecedentes:
    Dado que existe la tarea "Mudanza"

  Escenario: Una tarea nueva no tiene subtareas
    Entonces al consultar las tareas "Mudanza" tiene las subtareas ""

  Escenario: Crear una subtarea solo con nombre
    Cuando añado a "Mudanza" la subtarea "  Embalar libros  "
    Entonces la API responde 201 con "Mudanza" y sus subtareas "Embalar libros: -, -, pendiente"
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar libros: -, -, pendiente"

  Escenario: Crear una subtarea con persona asignada y prioridad
    Cuando añado a "Mudanza" la subtarea "Contratar camión" asignada a "  Ana  " con prioridad 2
    Entonces la API responde 201 con "Mudanza" y sus subtareas "Contratar camión: Ana, 2, pendiente"
    Y el catálogo de personas es "Ana"

  Escenario: La persona asignada reutiliza la del catálogo con su grafía
    Dado que existe la tarea "Viaje" asignada a "Ana"
    Cuando añado a "Mudanza" la subtarea "Contratar camión" asignada a "ANA" con prioridad 1
    Entonces la API responde 201 con "Mudanza" y sus subtareas "Contratar camión: Ana, 1, pendiente"
    Y el catálogo de personas es "Ana"

  Escenario: Las subtareas se devuelven por orden de alta
    Cuando añado a "Mudanza" la subtarea "B"
    Y añado a "Mudanza" la subtarea "A"
    Y añado a "Mudanza" la subtarea "C"
    Entonces al consultar las tareas "Mudanza" tiene las subtareas "B: -, -, pendiente; A: -, -, pendiente; C: -, -, pendiente"

  Escenario: Marcar una subtarea como resuelta y volver a abrirla
    Dado que "Mudanza" tiene las subtareas "Embalar, Limpiar"
    Cuando marco la subtarea "Embalar" de "Mudanza" como resuelta
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: -, -, resuelta; Limpiar: -, -, pendiente"
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: -, -, resuelta; Limpiar: -, -, pendiente"
    Cuando marco la subtarea "Embalar" de "Mudanza" como pendiente
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: -, -, pendiente; Limpiar: -, -, pendiente"

  Escenario: Eliminar una subtarea
    Dado que "Mudanza" tiene las subtareas "Embalar, Limpiar"
    Cuando elimino la subtarea "Embalar" de "Mudanza"
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Limpiar: -, -, pendiente"
    Y al consultar las tareas "Mudanza" tiene las subtareas "Limpiar: -, -, pendiente"

  Escenario: Editar la tarea o cambiar su tipo no altera sus subtareas
    Dado que "Mudanza" tiene las subtareas "Embalar, Limpiar"
    Y la subtarea "Limpiar" de "Mudanza" está resuelta
    Cuando edito "Mudanza" como oportunidad
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: -, -, pendiente; Limpiar: -, -, resuelta"
    Cuando edito "Mudanza" sin tipo
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: -, -, pendiente; Limpiar: -, -, resuelta"
    Cuando marco "Mudanza" como completada
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: -, -, pendiente; Limpiar: -, -, resuelta"

  Esquema del escenario: Se rechaza una subtarea con datos inválidos
    Cuando intento añadir a "Mudanza" una subtarea con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y al consultar las tareas "Mudanza" tiene las subtareas ""
    Y el catálogo de personas es ""

    Ejemplos:
      | cuerpo                                         |
      | {}                                             |
      | {"nombre": ""}                                 |
      | {"nombre": "   "}                              |
      | {"nombre": null}                               |
      | {"nombre": 5}                                  |
      | {"nombre": "A", "asignado": ""}                |
      | {"nombre": "A", "asignado": "  "}              |
      | {"nombre": "A", "prioridad": 0}                |
      | {"nombre": "A", "prioridad": 6}                |
      | {"nombre": "A", "prioridad": "2"}              |
      | {"nombre": "A", "prioridad": 2.5}              |
      | {"nombre": "A", "prioridad": true}             |

  Escenario: Se rechaza un nombre de más de 200 caracteres
    Cuando intento añadir a "Mudanza" una subtarea con un nombre de 201 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Y al consultar las tareas "Mudanza" tiene las subtareas ""

  Escenario: Se admite un nombre de 200 caracteres y una persona de 100
    Cuando añado a "Mudanza" una subtarea con un nombre de 200 caracteres asignada a una persona de 100
    Entonces la API responde 201 con una subtarea de nombre de 200 caracteres y persona de 100

  Escenario: Se rechaza una persona asignada de más de 100 caracteres
    Cuando intento añadir a "Mudanza" una subtarea asignada a una persona de 101 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Y el catálogo de personas es ""

  Esquema del escenario: Se rechaza un estado de la subtarea que no es un booleano
    Dado que "Mudanza" tiene las subtareas "Embalar"
    Cuando intento cambiar la subtarea "Embalar" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: -, -, pendiente"

    Ejemplos:
      | cuerpo                |
      | {"resuelta": "true"}  |
      | {"resuelta": 1}       |
      | {"resuelta": null}    |
      | {}                    |

  Escenario: Se rechaza añadir una subtarea a una tarea que no existe
    Cuando intento añadir la subtarea "Embalar" asignada a "Luis" a la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y el catálogo de personas es ""

  Escenario: Se rechaza cambiar o eliminar una subtarea de una tarea que no existe
    Dado que "Mudanza" tiene las subtareas "Embalar"
    Cuando intento marcar como resuelta la subtarea "Embalar" de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Cuando intento eliminar la subtarea "Embalar" de la tarea con id 999999
    Entonces la API responde que no existe la tarea con id 999999
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: -, -, pendiente"

  Escenario: Se rechaza cambiar o eliminar una subtarea que no existe
    Cuando intento marcar como resuelta la subtarea con id 999999 de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea con id 999999
    Cuando intento eliminar la subtarea con id 999999 de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea con id 999999

  Escenario: Se rechaza cambiar o eliminar la subtarea de otra tarea
    Dado que existe la tarea "Viaje" asignada a "Ana"
    Y que "Viaje" tiene las subtareas "Reservar"
    Cuando intento marcar como resuelta la subtarea "Reservar" de "Viaje" a través de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea "Reservar" de "Viaje"
    Cuando intento eliminar la subtarea "Reservar" de "Viaje" a través de "Mudanza"
    Entonces la API responde que "Mudanza" no tiene la subtarea "Reservar" de "Viaje"
    Y al consultar las tareas "Viaje" tiene las subtareas "Reservar: -, -, pendiente"

  Escenario: Editar una subtarea sustituye su nombre, persona y prioridad y conserva su estado
    Dado que "Mudanza" tiene las subtareas "Embalar, Limpiar"
    Y la subtarea "Embalar" de "Mudanza" está resuelta
    Cuando edito la subtarea "Embalar" de "Mudanza" con el cuerpo {"nombre": "  Embalar libros  ", "asignado": "  Ana  ", "prioridad": 3}
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar libros: Ana, 3, resuelta; Limpiar: -, -, pendiente"
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar libros: Ana, 3, resuelta; Limpiar: -, -, pendiente"
    Y el catálogo de personas es "Ana"

  Esquema del escenario: Editar una subtarea sin persona o sin prioridad las vacía
    Dado que "Mudanza" tiene la subtarea "Embalar" asignada a "Ana" con prioridad 2
    Cuando edito la subtarea "Embalar" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API responde 200 con "Mudanza" y sus subtareas "<subtareas>"
    Y al consultar las tareas "Mudanza" tiene las subtareas "<subtareas>"
    Y el catálogo de personas es "Ana"

    Ejemplos:
      | cuerpo                                                    | subtareas              |
      | {"nombre": "Embalar"}                                     | Embalar: -, -, pendiente  |
      | {"nombre": "Embalar", "asignado": null, "prioridad": null} | Embalar: -, -, pendiente  |
      | {"nombre": "Embalar", "prioridad": 2}                     | Embalar: -, 2, pendiente  |
      | {"nombre": "Embalar", "asignado": "Ana"}                  | Embalar: Ana, -, pendiente |

  Escenario: Editar la persona asignada reutiliza la del catálogo o la da de alta
    Dado que existe la tarea "Viaje" asignada a "Ana"
    Y que "Mudanza" tiene las subtareas "Embalar, Limpiar"
    Cuando edito la subtarea "Embalar" de "Mudanza" con el cuerpo {"nombre": "Embalar", "asignado": "ANA"}
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: Ana, -, pendiente; Limpiar: -, -, pendiente"
    Cuando edito la subtarea "Limpiar" de "Mudanza" con el cuerpo {"nombre": "Limpiar", "asignado": "Luis"}
    Entonces la API responde 200 con "Mudanza" y sus subtareas "Embalar: Ana, -, pendiente; Limpiar: Luis, -, pendiente"
    Y el catálogo de personas es "Ana, Luis"

  Escenario: Se admite editar una subtarea con un nombre de 200 caracteres y una persona de 100
    Dado que "Mudanza" tiene las subtareas "Embalar"
    Cuando edito la subtarea "Embalar" de "Mudanza" con un nombre de 200 caracteres y una persona de 100
    Entonces la API responde 200 con una subtarea de nombre de 200 caracteres y persona de 100

  Esquema del escenario: Se rechaza editar una subtarea con datos inválidos
    Dado que "Mudanza" tiene la subtarea "Embalar" asignada a "Ana" con prioridad 2
    Cuando edito la subtarea "Embalar" de "Mudanza" con el cuerpo <cuerpo>
    Entonces la API rechaza la petición por datos inválidos
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: Ana, 2, pendiente"
    Y el catálogo de personas es "Ana"

    Ejemplos:
      | cuerpo                                             |
      | {}                                                 |
      | {"nombre": ""}                                     |
      | {"nombre": "   "}                                  |
      | {"nombre": null}                                   |
      | {"nombre": 5}                                      |
      | {"asignado": "Luis", "prioridad": 3}               |
      | {"nombre": "A", "asignado": ""}                    |
      | {"nombre": "A", "asignado": "  "}                  |
      | {"nombre": "A", "asignado": "Luis", "prioridad": 0} |
      | {"nombre": "A", "asignado": "Luis", "prioridad": 6} |
      | {"nombre": "A", "prioridad": "2"}                  |
      | {"nombre": "A", "prioridad": 2.5}                  |
      | {"nombre": "A", "prioridad": true}                 |

  Escenario: Se rechaza editar una subtarea con un nombre de 201 caracteres o una persona de 101
    Dado que "Mudanza" tiene la subtarea "Embalar" asignada a "Ana" con prioridad 2
    Cuando intento editar la subtarea "Embalar" de "Mudanza" con un nombre de 201 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Cuando intento editar la subtarea "Embalar" de "Mudanza" con una persona de 101 caracteres
    Entonces la API rechaza la petición por datos inválidos
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: Ana, 2, pendiente"
    Y el catálogo de personas es "Ana"

  Escenario: Se rechaza editar una subtarea de una tarea que no existe sin dar de alta a la persona
    Dado que "Mudanza" tiene las subtareas "Embalar"
    Cuando intento editar la subtarea "Embalar" de la tarea con id 999999 asignándola a "Luis"
    Entonces la API responde que no existe la tarea con id 999999
    Y al consultar las tareas "Mudanza" tiene las subtareas "Embalar: -, -, pendiente"
    Y el catálogo de personas es ""

  Escenario: Se rechaza editar una subtarea que no existe sin dar de alta a la persona
    Cuando intento editar la subtarea con id 999999 de "Mudanza" asignándola a "Luis"
    Entonces la API responde que "Mudanza" no tiene la subtarea con id 999999
    Y el catálogo de personas es ""

  Escenario: Se rechaza editar la subtarea de otra tarea
    Dado que existe la tarea "Viaje" asignada a "Ana"
    Y que "Viaje" tiene las subtareas "Reservar"
    Cuando intento editar la subtarea "Reservar" de "Viaje" a través de "Mudanza" asignándola a "Luis"
    Entonces la API responde que "Mudanza" no tiene la subtarea "Reservar" de "Viaje"
    Y al consultar las tareas "Viaje" tiene las subtareas "Reservar: -, -, pendiente"
    Y al consultar las tareas "Mudanza" tiene las subtareas ""
    Y el catálogo de personas es "Ana"
