from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db_helpers.models import TimeSelection, User, SessionLocal, TimeChoice, NumberChoice, NumberSelection
from data_interpretations.time_interpretations import time_interpretations
import locale

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


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


def fetch_stat_for_time_range(message, start_date, end_date, stat_type):
    print('stat', stat_type)
    with SessionLocal() as session:
        user = session.query(User).filter_by(tg_id=message.chat.id).first()

        if not user:
            return "Пользователь не найден."

        if stat_type == "time":
            # Существующая логика для времени
            time_selections = session.query(TimeSelection).filter(
                and_(
                    TimeSelection.user_id == user.id,
                    TimeSelection.timestamp >= start_date,
                    TimeSelection.timestamp <= end_date
                )
            ).all()

            if not time_selections:
                return f"У вас нет выборов времени с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}."

            time_stats = defaultdict(int)
            for selection in time_selections:
                time_stats[selection.time_choice.choice] += 1

            sorted_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)

            response = f"<b>Статистика времени с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}:</b>\n\n"

            for time_choice, count in sorted_stats:
                interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
                if interpretation:
                    response += f"<b>{time_choice}</b>: {count} раз(а) - {interpretation.interpretation}\n"

        elif stat_type == "numbers":
            number_selections = session.query(NumberSelection).filter(
                and_(
                    NumberSelection.user_id == user.id,
                    NumberSelection.timestamp >= start_date,
                    NumberSelection.timestamp <= end_date
                )
            ).all()

            if not number_selections:
                return f"У вас нет выборов чисел с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}."

            number_stats = defaultdict(int)
            for selection in number_selections:
                number_stats[selection.number_choice.number] += 1

            sorted_stats = sorted(number_stats.items(), key=lambda x: x[1], reverse=True)

            response = f"<b>Статистика чисел с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}:</b>\n\n"

            for number, count in sorted_stats:
                interpretation = session.query(NumberChoice).filter_by(number=number).first()
                if interpretation:
                    response += f"<b>{number}</b>: {count} раз(а) - {interpretation.interpretation}\n\n"

        return response.strip()
