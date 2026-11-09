from sqlalchemy import text
from sqlalchemy.orm import Session


def test_la_sesion_conecta_con_la_base_de_datos(sesion_bd: Session) -> None:
    assert sesion_bd.execute(text("SELECT 1")).scalar_one() == 1
