from gestor_tareas.infraestructura.seguridad.gestor_contrasenas import (
    hashear_contrasena,
    verificar_contrasena,
)


def test_una_contrasena_hasheada_se_verifica_correctamente() -> None:
    hash_generado = hashear_contrasena("mi-contrasena-segura")

    assert verificar_contrasena("mi-contrasena-segura", hash_generado) is True


def test_una_contrasena_incorrecta_no_se_verifica() -> None:
    hash_generado = hashear_contrasena("mi-contrasena-segura")

    assert verificar_contrasena("otra-contrasena", hash_generado) is False
