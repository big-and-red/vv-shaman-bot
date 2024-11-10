from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db_helpers.models import TimeSelection, User, SessionLocal, TimeChoice
from data_interpretations.time_interpretations import time_interpretations


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


def fetch_stat_for_time_range(message, start_date, end_date):
    """
    Функция для получения статистики по выбранному промежутку времени.
    :param message: Сообщение Telegram, содержащее информацию о пользователе.
    :param start_date: Начальная дата промежутка.
    :param end_date: Конечная дата промежутка.
    """
    with SessionLocal() as session:
        # Находим пользователя по Telegram ID
        user = session.query(User).filter_by(tg_id=message.chat.id).first()

        if not user:
            response = "Пользователь не найден."
            return response

        # Получаем все выборы времени для данного пользователя за указанный промежуток
        time_selections = session.query(TimeSelection).filter(
            and_(
                TimeSelection.user_id == user.id,
                TimeSelection.timestamp >= start_date,
                TimeSelection.timestamp <= end_date
            )
        ).all()

        if not time_selections:
            response = f"У вас нет выборов времени с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}."
            return response

        time_stats = defaultdict(int)

        # Собираем статистику по временам
        for selection in time_selections:
            # Увеличиваем счетчик для выбранного времени
            time_stats[selection.time_choice.choice] += 1

        # Сортируем статистику по количеству выборов (от большего к меньшему)
        sorted_time_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)

        # Формируем ответ с трактовками
        response = f"<b>Статистика с {start_date.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}:</b>\n\n"
        for time_choice, count in sorted_time_stats:
            # Получаем трактовку времени
            interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
            if interpretation:
                response += f"<b>{time_choice}</b>: {count} раз(а) - {interpretation.interpretation}\n"

        # Удалите пустые строки в конце ответа
        response = response.strip()

        # Отправляем сообщение с результатами
        return response
