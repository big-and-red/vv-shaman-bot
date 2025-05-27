import logging
from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db_helpers.models import TimeSelection, User, SessionLocal, TimeChoice, NumberChoice, NumberSelection
import locale

# Настройка логирования
logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    logger.warning("Не удалось установить русскую локаль, используется системная локаль")


def get_user_time_statistics(session: Session, tg_id: int):
    """
    Получает статистику времен для пользователя

    :param session: Сессия SQLAlchemy
    :param tg_id: Telegram ID пользователя
    :return: Словарь с статистикой
    """
    try:
        user = session.query(User).filter(User.tg_id == tg_id).first()

        # Если пользователь не найден, возвращаем пустой словарь
        if not user:
            logger.warning(f"Пользователь с tg_id {tg_id} не найден")
            return {}

        # Инициализируем словарь для хранения статистики
        statistics = defaultdict(lambda: {"count": 0, "interpretation": ""})

        # Получаем все выборы времени пользователя
        time_selections = session.query(TimeSelection).filter_by(user_id=user.id).all()

        # Обрабатываем выборы времени
        for selection in time_selections:
            time_choice = selection.time_choice.choice
            interpretation = selection.time_choice.interpretation
            statistics[time_choice]["count"] += 1
            statistics[time_choice]["interpretation"] = interpretation

        return statistics
    except Exception as e:
        logger.error(f"Ошибка при получении статистики времени: {e}", exc_info=True)
        return {}


def fetch_stat_for_time_range(message, start_date, end_date, stat_type):
    """
    Получает статистику за указанный промежуток времени

    :param message: Сообщение пользователя
    :param start_date: Начальная дата
    :param end_date: Конечная дата
    :param stat_type: Тип статистики ('time' или 'numbers')
    :return: Строка с результатами
    """
    logger.info(f"Запрос статистики типа {stat_type} с {start_date} по {end_date}")

    try:
        with SessionLocal() as session:
            user = session.query(User).filter_by(tg_id=message.chat.id).first()

            if not user:
                logger.warning(f"Пользователь не найден: {message.chat.id}")
                return "Пользователь не найден."

            if stat_type == "time":
                # Получаем выборы времени в указанном диапазоне
                time_selections = session.query(TimeSelection).filter(
                    and_(
                        TimeSelection.user_id == user.id,
                        TimeSelection.timestamp >= start_date,
                        TimeSelection.timestamp <= end_date
                    )
                ).all()

                if not time_selections:
                    logger.info(f"Нет временных выборов в диапазоне для пользователя {user.id}")
                    return f"У вас нет выборов времени с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}."

                time_stats = defaultdict(int)
                for selection in time_selections:
                    time_stats[selection.time_choice.choice] += 1

                sorted_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)

                response = f"<b>Статистика времени с {start_date.strftime('%d %B %Y')} по {end_date.strftime('%d %B %Y')}:</b>\n\n"

                for time_choice, count in sorted_stats:
                    interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
                    if interpretation:
                        response += f"<b>{time_choice}</b>: {count} раз(а) - {interpretation.interpretation}\n\n"

            elif stat_type == "numbers":
                # Получаем выборы чисел в указанном диапазоне
                number_selections = session.query(NumberSelection).filter(
                    and_(
                        NumberSelection.user_id == user.id,
                        NumberSelection.timestamp >= start_date,
                        NumberSelection.timestamp <= end_date
                    )
                ).all()

                if not number_selections:
                    logger.info(f"Нет числовых выборов в диапазоне для пользователя {user.id}")
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
            else:
                logger.warning(f"Неизвестный тип статистики: {stat_type}")
                return "Неизвестный тип статистики."

            return response.strip()
    except Exception as e:
        logger.error(f"Ошибка при получении статистики за период: {e}", exc_info=True)
        return "Произошла ошибка при получении статистики. Пожалуйста, попробуйте позже."