USER_MAPPING = {
    1389473957: 1
}
async def get_user_id_by_tg(tg_id: int) -> int | None:
    return USER_MAPPING.get(tg_id, None)  # Возвращает Bitrix ID или None, если не найден