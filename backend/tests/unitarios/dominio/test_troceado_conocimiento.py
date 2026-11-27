"""Troceado del texto de una página de Notion para el índice de Conocimiento."""

from gestor_tareas.dominio.conocimiento.troceado import trocear


def test_un_texto_corto_es_un_solo_trozo_sin_espacios_sobrantes() -> None:
    assert trocear("  Título\n\nPrimer párrafo.\n  \nSegundo.  ") == [
        "Título\nPrimer párrafo.\nSegundo."
    ]


def test_un_texto_vacio_o_solo_con_espacios_no_da_trozos() -> None:
    assert trocear("") == []
    assert trocear(" \n \n") == []


def test_parte_por_los_parrafos_sin_pasar_del_tamano_y_solapa_el_ultimo_parrafo() -> None:
    parrafos = [f"P{i} " + "x" * 46 for i in range(10)]  # 50 caracteres cada uno

    trozos = trocear("\n".join(parrafos), tamano=160, solape=60)

    assert all(len(t) <= 160 for t in trozos)
    # Cada trozo empieza con el último párrafo del anterior (cabe en el solape).
    for anterior, siguiente in zip(trozos, trozos[1:], strict=False):
        assert siguiente.split("\n")[0] == anterior.split("\n")[-1]
    # No se pierde ningún párrafo y no se parte ninguno.
    vistos = {p for t in trozos for p in t.split("\n")}
    assert vistos == set(parrafos)
    assert len(trozos) > 1


def test_sin_solape_ningun_parrafo_se_repite() -> None:
    parrafos = [f"P{i} " + "y" * 46 for i in range(6)]

    trozos = trocear("\n".join(parrafos), tamano=110, solape=0)

    assert [p for t in trozos for p in t.split("\n")] == parrafos


def test_un_parrafo_mas_largo_que_el_tamano_se_parte_por_los_espacios() -> None:
    palabras = [f"palabra{i:03d}" for i in range(100)]  # 10 caracteres cada una
    texto = " ".join(palabras)

    trozos = trocear(texto, tamano=120, solape=25)

    assert all(len(t) <= 120 for t in trozos)
    # Ninguna palabra queda partida y todas aparecen.
    vistas = [p for t in trozos for p in t.split(" ")]
    assert set(vistas) == set(palabras)
    assert all(p in palabras for p in vistas)
    # Con solape, cada trozo repite el final del anterior.
    assert trozos[1].split(" ")[0] in trozos[0]


def test_una_palabra_mas_larga_que_el_tamano_se_parte_a_la_fuerza() -> None:
    trozos = trocear("z" * 250, tamano=100, solape=0)

    assert trozos == ["z" * 100, "z" * 100, "z" * 50]


def test_el_tamano_por_defecto_ronda_los_1200_caracteres() -> None:
    texto = "\n".join("Párrafo " + "w" * 290 for _ in range(20))  # ~300 cada uno

    trozos = trocear(texto)

    assert all(len(t) <= 1200 for t in trozos)
    assert max(len(t) for t in trozos) > 900
