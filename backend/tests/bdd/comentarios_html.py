"""Lo que guarda la API para los comentarios que se escriben en los escenarios."""

from html import escape


def html_guardado(texto: str) -> str:
    """El HTML que la API guarda y devuelve para un comentario de un escenario.

    Los escenarios escriben los comentarios como texto plano: la API guarda un
    párrafo por línea, con los caracteres especiales escapados. Un texto que ya
    empieza por una etiqueta se da por HTML saneado y se compara tal cual.
    """
    if texto.startswith("<"):
        return texto
    return "".join(f"<p>{escape(linea, quote=False)}</p>" for linea in texto.split("\n"))
