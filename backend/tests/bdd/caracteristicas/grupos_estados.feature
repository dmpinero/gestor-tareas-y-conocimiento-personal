# language: es
Característica: Grupos de estados
  Como persona usuaria de la aplicación
  Quiero definir grupos de estados, cada uno con su nombre y su conjunto de estados
  Para asignarlos a las tareas y mover las tareas entre cualquiera de sus estados

  Escenario: Sin grupos, el listado está vacío
    Dado que no hay grupos de estados
    Cuando consulto los grupos de estados
    Entonces la API devuelve una lista de grupos vacía

  Escenario: Crear un grupo lo guarda sin estados y sin los espacios de los extremos
    Dado que no hay grupos de estados
    Cuando creo el grupo de estados "  Desarrollo  "
    Entonces la API responde que el grupo "Desarrollo" se ha creado sin estados
    Y se guardan los grupos "Desarrollo"

  Escenario: Los grupos se listan por nombre con sus estados en orden
    Dado que existe el grupo "Ventas" con los estados "Nueva, Ganada"
    Y que existe el grupo "desarrollo" con los estados "Pendiente, En curso, Hecha"
    Cuando consulto los grupos de estados
    Entonces la API devuelve los grupos "desarrollo, Ventas"
    Y el grupo "desarrollo" tiene los estados "Pendiente, En curso, Hecha"
    Y el grupo "Ventas" tiene los estados "Nueva, Ganada"

  Esquema del escenario: Se rechaza un grupo con un nombre inválido
    Dado que existe el grupo "Ventas" con los estados "Nueva"
    Cuando intento crear un grupo de estados con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y se guardan los grupos "Ventas"

    Ejemplos:
      | nombre           |
      | vacío            |
      | solo de espacios |
      | con espacio duro |
      | de 51 caracteres |
      | ausente          |
      | que no es texto  |

  Escenario: Se admite un nombre de grupo de 50 caracteres
    Dado que no hay grupos de estados
    Cuando creo un grupo de estados con un nombre de 50 caracteres
    Entonces la API responde que el grupo se ha creado con ese nombre

  Esquema del escenario: No puede haber dos grupos con el mismo nombre
    Dado que existe el grupo "Ventas" con los estados "Nueva"
    Cuando creo el grupo de estados "<nombre>"
    Entonces la API responde que ya existe un grupo de estados llamado "<nombre>"
    Y se guardan los grupos "Ventas"

    Ejemplos:
      | nombre |
      | Ventas |
      | VENTAS |

  Escenario: Renombrar un grupo conserva sus estados
    Dado que existe el grupo "Ventas" con los estados "Nueva, Ganada"
    Cuando renombro el grupo "Ventas" a " Comercial "
    Entonces la API responde con el grupo "Comercial" y los estados "Nueva, Ganada"
    Y se guardan los grupos "Comercial"

  Escenario: Renombrar un grupo cambiando solo las mayúsculas
    Dado que existe el grupo "Ventas" con los estados "Nueva"
    Cuando renombro el grupo "Ventas" a "VENTAS"
    Entonces la API responde con el grupo "VENTAS" y los estados "Nueva"

  Escenario: No se puede renombrar un grupo con el nombre de otro
    Dado que existe el grupo "Ventas" con los estados "Nueva"
    Y que existe el grupo "Desarrollo" con los estados "Pendiente"
    Cuando renombro el grupo "Desarrollo" a "ventas"
    Entonces la API responde que ya existe un grupo de estados llamado "ventas"
    Y se guardan los grupos "Desarrollo, Ventas"

  Escenario: Eliminar un grupo borra sus estados
    Dado que existe el grupo "Ventas" con los estados "Nueva, Ganada"
    Y que existe el grupo "Desarrollo" con los estados "Pendiente"
    Cuando elimino el grupo "Ventas"
    Entonces la API responde que el grupo se ha eliminado
    Y se guardan los grupos "Desarrollo"
    Y se guardan los estados "Pendiente"

  Escenario: Añadir un estado lo pone al final del grupo
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso"
    Cuando añado el estado " Hecha " al grupo "Desarrollo"
    Entonces la API responde 201 con el grupo "Desarrollo" y los estados "Pendiente, En curso, Hecha"
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso, Hecha"

  Escenario: El mismo nombre de estado puede estar en grupos distintos
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente"
    Y que existe el grupo "Ventas" con los estados "Nueva"
    Cuando añado el estado "Pendiente" al grupo "Ventas"
    Entonces la API responde 201 con el grupo "Ventas" y los estados "Nueva, Pendiente"

  Esquema del escenario: No puede haber dos estados con el mismo nombre en un grupo
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso"
    Cuando añado el estado "<nombre>" al grupo "Desarrollo"
    Entonces la API responde que ya existe un estado llamado "<nombre>" en el grupo "Desarrollo"
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso"

    Ejemplos:
      | nombre    |
      | Pendiente |
      | EN CURSO  |

  Esquema del escenario: Se rechaza un estado con un nombre inválido
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente"
    Cuando intento añadir al grupo "Desarrollo" un estado con un nombre <nombre>
    Entonces la API rechaza la operación por datos inválidos
    Y el grupo "Desarrollo" guarda los estados "Pendiente"

    Ejemplos:
      | nombre           |
      | vacío            |
      | solo de espacios |
      | de 51 caracteres |
      | ausente          |

  Escenario: Renombrar un estado conserva su posición
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso, Hecha"
    Cuando renombro el estado "En curso" del grupo "Desarrollo" a "  Haciendo "
    Entonces la API responde con el grupo "Desarrollo" y los estados "Pendiente, Haciendo, Hecha"
    Y el grupo "Desarrollo" guarda los estados "Pendiente, Haciendo, Hecha"

  Escenario: No se puede renombrar un estado con el nombre de otro del grupo
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso"
    Cuando renombro el estado "En curso" del grupo "Desarrollo" a "pendiente"
    Entonces la API responde que ya existe un estado llamado "pendiente" en el grupo "Desarrollo"
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso"

  Esquema del escenario: Eliminar un estado sin tareas renumera los siguientes
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso, Revisión, Hecha"
    Cuando elimino el estado "<eliminado>" del grupo "Desarrollo"
    Entonces la API responde con el grupo "Desarrollo" y los estados "<quedan>"
    Y el grupo "Desarrollo" guarda los estados "<quedan>"

    Ejemplos:
      | eliminado | quedan                       |
      | Pendiente | En curso, Revisión, Hecha    |
      | Revisión  | Pendiente, En curso, Hecha   |
      | Hecha     | Pendiente, En curso, Revisión |

  Escenario: Eliminar el último estado deja el grupo sin estados
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente"
    Cuando elimino el estado "Pendiente" del grupo "Desarrollo"
    Entonces la API responde con el grupo "Desarrollo" sin estados
    Y el grupo "Desarrollo" no guarda estados

  Escenario: Reordenar los estados recalcula sus posiciones
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso, Revisión, Hecha"
    Cuando reordeno los estados del grupo "Desarrollo" como "Revisión, Pendiente, Hecha, En curso"
    Entonces la API responde con el grupo "Desarrollo" y los estados "Revisión, Pendiente, Hecha, En curso"
    Y el grupo "Desarrollo" guarda los estados "Revisión, Pendiente, Hecha, En curso"

  Esquema del escenario: Se rechaza un orden que no incluye cada estado del grupo exactamente una vez
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente, En curso, Hecha"
    Y que existe el grupo "Ventas" con los estados "Nueva"
    Cuando intento reordenar los estados del grupo "Desarrollo" con un orden <orden>
    Entonces la API rechaza la operación por datos inválidos
    Y el grupo "Desarrollo" guarda los estados "Pendiente, En curso, Hecha"

    Ejemplos:
      | orden                          |
      | con un estado repetido         |
      | al que le falta un estado      |
      | con un estado de otro grupo    |
      | con un estado que no existe    |
      | vacío                          |
      | con ids que no son enteros     |
      | ausente                        |

  Esquema del escenario: Un grupo que no existe responde 404
    Dado que existe el grupo "Ventas" con los estados "Nueva"
    Cuando intento <operacion> un grupo que no existe
    Entonces la API responde que el grupo de estados no existe
    Y se guardan los grupos "Ventas"

    Ejemplos:
      | operacion                        |
      | renombrar                        |
      | eliminar                         |
      | añadir un estado a               |
      | renombrar un estado de           |
      | eliminar un estado de            |
      | reordenar los estados de         |

  Esquema del escenario: Un estado que no es del grupo responde 404
    Dado que existe el grupo "Desarrollo" con los estados "Pendiente"
    Y que existe el grupo "Ventas" con los estados "Nueva"
    Cuando intento <operacion> el estado "<estado>" en el grupo "Desarrollo"
    Entonces la API responde que el estado no es del grupo "Desarrollo"
    Y el grupo "Desarrollo" guarda los estados "Pendiente"
    Y el grupo "Ventas" guarda los estados "Nueva"

    Ejemplos:
      | operacion | estado     |
      | renombrar | Nueva      |
      | eliminar  | Nueva      |
      | renombrar | inexistente |
      | eliminar  | inexistente |
