from passlib.context import CryptContext

_contexto_hash = CryptContext(schemes=["argon2"], deprecated="auto")


def hashear_contrasena(contrasena_en_claro: str) -> str:
    """Genera el hash seguro (argon2) de una contraseña en texto claro."""
    return _contexto_hash.hash(contrasena_en_claro)


def verificar_contrasena(contrasena_en_claro: str, hash_almacenado: str) -> bool:
    """Comprueba si una contraseña en claro coincide con el hash almacenado."""
    return _contexto_hash.verify(contrasena_en_claro, hash_almacenado)
