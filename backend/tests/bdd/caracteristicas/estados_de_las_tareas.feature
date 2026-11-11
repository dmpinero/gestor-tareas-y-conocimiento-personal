# language: es
Característica: Estados de las tareas según su grupo de estados
  Como persona usuaria de la aplicación
  Quiero asignar a cada tarea uno de los grupos de estados definidos
  Para que herede sus estados y pueda moverla entre cualquiera de ellos

  Antecedentes:
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso, Hecha"
    Y que existe el grupo "Ventas" con los estados "Nueva, Ganada"
    Y que existe el grupo "Vacío" sin estados

  Escenario: Una tarea creada sin grupo no tiene grupo ni estado
    Cuando creo la tarea "Informe" sin grupo de estados
    Entonces la API responde 201 con la tarea sin grupo ni estado
    Y la tarea "Informe" se guarda sin grupo ni estado

  Escenario: Al crear una tarea con un grupo queda en su primer estado
    Cuando creo la tarea "Informe" con el grupo "Desarrollo"
    Entonces la API responde 201 con la tarea en el grupo "Desarrollo" y el estado "Pendiente"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

  Escenario: El primer estado es el primero según el orden del grupo
    Dado que reordeno los estados del grupo "Desarrollo" como "Hecha, Pendiente, En curso"
    Cuando creo la tarea "Informe" con el grupo "Desarrollo"
    Entonces la API responde 201 con la tarea en el grupo "Desarrollo" y el estado "Hecha"

  Escenario: No se puede crear una tarea con un grupo que no existe
    Cuando creo la tarea "Informe" con un grupo que no existe
    Entonces la API rechaza la tarea porque no existe el grupo
    Y no se guarda ninguna tarea

  Escenario: No se puede crear una tarea con un grupo sin estados
    Cuando creo la tarea "Informe" con el grupo "Vacío"
    Entonces la API rechaza la tarea porque el grupo "Vacío" no tiene estados
    Y no se guarda ninguna tarea

  Esquema del escenario: Se rechaza un grupo de estados que no es un id entero
    Cuando creo la tarea "Informe" con grupo_estados_id <valor>
    Entonces la API rechaza la operación por datos inválidos
    Y no se guarda ninguna tarea

    Ejemplos:
      | valor  |
      | "1"    |
      | true   |
      | 1.5    |

  Escenario: Al editar una tarea sin grupo para asignarle uno queda en su primer estado
    Dado que existe la tarea "Informe" sin grupo de estados
    Cuando edito la tarea "Informe" con el grupo "Ventas"
    Entonces la API responde 200 con la tarea en el grupo "Ventas" y el estado "Nueva"
    Y la tarea "Informe" se guarda en el grupo "Ventas" y el estado "Nueva"

  Escenario: Editar una tarea manteniendo su grupo conserva su estado
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Y que muevo la tarea "Informe" al estado "En curso"
    Cuando edito la tarea "Informe" con el grupo "Desarrollo"
    Entonces la API responde 200 con la tarea en el grupo "Desarrollo" y el estado "En curso"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "En curso"

  Escenario: Al cambiar el grupo de una tarea queda en el primer estado del nuevo
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Y que muevo la tarea "Informe" al estado "Hecha"
    Cuando edito la tarea "Informe" con el grupo "Ventas"
    Entonces la API responde 200 con la tarea en el grupo "Ventas" y el estado "Nueva"
    Y la tarea "Informe" se guarda en el grupo "Ventas" y el estado "Nueva"

  Esquema del escenario: Editar una tarea sin grupo de estados le quita el grupo y el estado
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando edito la tarea "Informe" con grupo_estados_id <valor>
    Entonces la API responde 200 con la tarea sin grupo ni estado
    Y la tarea "Informe" se guarda sin grupo ni estado

    Ejemplos:
      | valor   |
      | null    |
      | ausente |

  Esquema del escenario: No se puede editar una tarea con un grupo inválido
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Y que muevo la tarea "Informe" al estado "En curso"
    Cuando edito la tarea "Informe" con <grupo>
    Entonces la API rechaza la tarea porque <motivo>
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "En curso"

    Ejemplos:
      | grupo                  | motivo                                 |
      | un grupo que no existe | no existe el grupo                     |
      | el grupo "Vacío"       | el grupo "Vacío" no tiene estados      |

  Escenario: Una tarea se mueve a cualquier estado de su grupo, en cualquier orden
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando muevo la tarea "Informe" al estado "Hecha"
    Entonces la API responde 200 con la tarea en el grupo "Desarrollo" y el estado "Hecha"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Hecha"
    Cuando muevo la tarea "Informe" al estado "Pendiente"
    Entonces la API responde 200 con la tarea en el grupo "Desarrollo" y el estado "Pendiente"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

  Escenario: Mover una tarea conserva el resto de sus datos
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando muevo la tarea "Informe" al estado "En curso"
    Entonces el resto de datos de la tarea "Informe" no cambia

  Escenario: No se puede mover una tarea que no existe
    Cuando muevo una tarea que no existe al estado "Pendiente"
    Entonces la API responde que la tarea no existe

  Escenario: No se puede mover una tarea sin grupo
    Dado que existe la tarea "Informe" sin grupo de estados
    Cuando muevo la tarea "Informe" al estado "Pendiente"
    Entonces la API rechaza el cambio de estado porque la tarea no tiene grupo
    Y la tarea "Informe" se guarda sin grupo ni estado

  Esquema del escenario: No se puede mover una tarea a un estado que no es de su grupo
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando muevo la tarea "Informe" al estado "<estado>"
    Entonces la API rechaza el cambio de estado porque el estado no es del grupo "Desarrollo"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

    Ejemplos:
      | estado      |
      | Nueva       |
      | inexistente |

  Esquema del escenario: Se rechaza un cambio de estado con un id que no es entero
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando cambio el estado de la tarea "Informe" con el cuerpo <cuerpo>
    Entonces la API rechaza la operación por datos inválidos
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

    Ejemplos:
      | cuerpo                 |
      | {"estado_id": "1"}     |
      | {"estado_id": true}    |
      | {"estado_id": null}    |
      | {}                     |

  Escenario: Cada grupo y cada estado cuentan sus tareas
    Dado que existe la tarea "A" con el grupo "Desarrollo"
    Y que existe la tarea "B" con el grupo "Desarrollo"
    Y que existe la tarea "C" con el grupo "Desarrollo"
    Y que muevo la tarea "C" al estado "Hecha"
    Y que existe la tarea "D" con el grupo "Ventas"
    Y que existe la tarea "E" sin grupo de estados
    Cuando consulto los grupos de estados
    Entonces el grupo "Desarrollo" tiene 3 tareas: "Pendiente" 2, "En curso" 0, "Hecha" 1
    Y el grupo "Ventas" tiene 1 tareas: "Nueva" 1, "Ganada" 0
    Y el grupo "Vacío" tiene 0 tareas

  Escenario: Renombrar un estado se refleja en sus tareas
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando renombro el estado "Pendiente" del grupo "Desarrollo" a "Por hacer"
    Y renombro el grupo "Desarrollo" a "Equipo"
    Entonces la tarea "Informe" se guarda en el grupo "Equipo" y el estado "Por hacer"

  Escenario: No se puede eliminar un estado con tareas sin indicar a dónde moverlas
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando elimino el estado "Pendiente" del grupo "Desarrollo"
    Entonces la API responde que el estado "Pendiente" tiene 1 tareas y hay que indicar a dónde moverlas
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso, Hecha"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

  Escenario: Eliminar un estado con tareas las mueve al estado indicado
    Dado que existe la tarea "A" con el grupo "Desarrollo"
    Y que existe la tarea "B" con el grupo "Desarrollo"
    Y que existe la tarea "C" con el grupo "Desarrollo"
    Y que muevo la tarea "C" al estado "Hecha"
    Cuando elimino el estado "Pendiente" del grupo "Desarrollo" moviendo sus tareas a "Hecha"
    Entonces la API responde con el grupo "Desarrollo" y los estados "En curso, Hecha"
    Y el estado "Hecha" del grupo "Desarrollo" tiene 3 tareas
    Y la tarea "A" se guarda en el grupo "Desarrollo" y el estado "Hecha"
    Y la tarea "B" se guarda en el grupo "Desarrollo" y el estado "Hecha"
    Y el grupo "Desarrollo" guarda los estados "En curso, Hecha"

  Esquema del escenario: Se rechaza mover las tareas de un estado eliminado a un estado inválido
    Dado que existe la tarea "Informe" con el grupo "Desarrollo"
    Cuando elimino el estado "Pendiente" del grupo "Desarrollo" moviendo sus tareas a "<destino>"
    Entonces la API responde que hay que mover las tareas a otro estado del grupo "Desarrollo"
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso, Hecha"
    Y la tarea "Informe" se guarda en el grupo "Desarrollo" y el estado "Pendiente"

    Ejemplos:
      | destino     |
      | Pendiente   |
      | Nueva       |
      | inexistente |

  Escenario: Eliminar un grupo deja sus tareas sin grupo ni estado
    Dado que existe la tarea "A" con el grupo "Desarrollo"
    Y que existe la tarea "B" con el grupo "Ventas"
    Cuando elimino el grupo "Desarrollo"
    Entonces la API responde que el grupo se ha eliminado
    Y la tarea "A" se guarda sin grupo ni estado
    Y la tarea "B" se guarda en el grupo "Ventas" y el estado "Nueva"
