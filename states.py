# states.py
# Здесь храним состояния пользователей

user_states = {}

# Возможные состояния
STATE_AWAITING_START_DATE = "awaiting_start_date"
STATE_AWAITING_END_DATE = "awaiting_end_date"
STATE_AWAITING_PREDEFINED_RANGE = "awaiting_predefined_range"
STATE_AWAITING_STAT_TYPE = 'awaiting_stat_type'



# Функции для работы с состояниями
def set_user_state(user_id, state, additional_data=None):
    """
    Обновляет состояние пользователя, сохраняя существующие данные.
    :param user_id: ID пользователя
    :param state: Новое состояние
    :param additional_data: Дополнительные данные для обновления состояния
    """
    if user_id not in user_states:
        user_states[user_id] = {}

    # Обновляем состояние
    user_states[user_id]['state'] = state

    # Обновляем дополнительные данные, не перезаписывая существующие
    if additional_data:
        user_states[user_id].update(additional_data)


def get_user_state(user_id):
    """
    Получает текущее состояние пользователя.
    :param user_id: ID пользователя
    :return: Словарь с состоянием или None, если состояние не установлено
    """
    return user_states.get(user_id, None)


def clear_user_state(user_id):
    """
    Очищает состояние пользователя.
    :param user_id: ID пользователя
    """
    if user_id in user_states:
        del user_states[user_id]
