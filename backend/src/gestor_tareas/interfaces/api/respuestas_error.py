RESPUESTA_NO_ENCONTRADO = {404: {"description": "La entidad referenciada no existe"}}
RESPUESTA_CONFLICTO = {
    409: {"description": "Nombre duplicado o la entidad tiene dependencias asociadas"}
}
# FastAPI devuelve 400 (no 422) cuando el cuerpo ni siquiera es JSON válido,
# antes de que Pydantic pueda validar los campos.
RESPUESTA_CUERPO_MALFORMADO = {400: {"description": "El cuerpo de la petición no es JSON válido"}}
RESPUESTA_FILTRO_INVALIDO = {
    422: {"description": "La combinación de filtros indicada no es válida"}
}
