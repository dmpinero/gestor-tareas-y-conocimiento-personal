import logging
import sys

from pythonjsonlogger.json import JsonFormatter


def configurar_registro_logs(nivel: str = "INFO") -> None:
    """Configura el logging raíz de la aplicación en formato JSON estructurado."""
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    raiz = logging.getLogger()
    raiz.handlers = [manejador]
    raiz.setLevel(nivel)
