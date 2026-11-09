# language: es
Característica: Comprobación del estado de salud de la API
  Como persona usuaria de la API
  Quiero poder comprobar si el servicio está operativo
  Para saber si puedo confiar en que la aplicación responde

  Escenario: La API está operativa
    Dado que el servicio está en marcha
    Cuando consulto el endpoint de salud
    Entonces la respuesta indica que el estado es correcto
