from collections import defaultdict
from sqlalchemy.orm import Session

from db_helpers.models import TimeSelection, User
from time_data.time_interpretations import time_interpretations


def get_user_time_statistics(session: Session, tg_id: int):
    # Получаем пользователя по tg_id
    user = session.query(User).filter(User.tg_id == str(tg_id)).first()

    # Если пользователь не найден, возвращаем пустой словарь
    if not user:
        return {}

    # Инициализируем словарь для хранения статистики
    statistics = defaultdict(lambda: {"count": 0, "interpretation": ""})

    # Получаем все выборы времени пользователя
    time_selections = user.selections

    # Обрабатываем выборы времени
    for selection in time_selections:
        time_choice = selection.time_choice.choice
        interpretation = selection.time_choice.interpretation
        statistics[time_choice]["count"] += 1
        statistics[time_choice]["interpretation"] = interpretation

    return statistics

