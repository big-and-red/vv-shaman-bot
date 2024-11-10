import logging
from collections import defaultdict
from datetime import datetime

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config_instance
from db_helpers.models import SessionLocal, TimeChoice, TimeRange, TimeSelection, User, NumberChoice
from data_interpretations.time_interpretations import time_interpretations
from states import set_user_state, STATE_AWAITING_START_DATE, STATE_AWAITING_PREDEFINED_RANGE
from utils.inline_calendar import TelegramCalendar
from utils.message_utils import generate_time_range_buttons
from utils.message_utils import send_long_message
from utils.stat_utils import get_user_time_statistics
from utils.sub_channel_checker import is_user_subscribed

calendar_instance = TelegramCalendar(locale="ru")
logger = logging.getLogger()

def register_command_handlers(bot: TeleBot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        with SessionLocal() as session:
            user = session.query(User).filter_by(tg_id=message.from_user.id).first()
            if not user:
                user = User(username=message.from_user.username, tg_id=message.from_user.id)
                session.add(user)  # Добавляем пользователя в сессию, если он новый
                session.commit()

        response_message = (
            "Этот бот поможет тебе записывать знаки Вселенной.\n\n"
            "*Всякий раз, когда ты видишь время, определенное сочетание цифр — это подсказка.*\n"
            "Если на протяжении долгого времени тебе раз за разом попадается одно и то же время, минимум 3 раза, "
            "— это подсказка прямо в лоб.\n\n"
            "*Команды*\n"
            "*/time* — Добавить временной знак.\n"
            "*/stat* — Твоя общая статистика.\n"
            "*/time_list* — Полный список временных знаков.\n\n"
            "Подписывайтесь на открытые каналы:\n"
            "[Артём ВВШ](https://t.me/strong_mvp)\n"
            "[Главком](https://t.me/arsenmarkarian)\n\n"
            "Автор бота — [Леон](https://t.me/smthng_hero)"
        )
        bot.send_message(message.chat.id, response_message, parse_mode="Markdown")

    @bot.message_handler(commands=['time'])
    def send_welcome(message):
        with SessionLocal() as session:
            time_ranges = session.query(TimeRange).all()  # Получаем все временные промежутки

            response_message = "Выберите временной промежуток:"

            markup = generate_time_range_buttons(time_ranges)

            bot.send_message(message.chat.id, response_message, reply_markup=markup)

    @bot.message_handler(commands=['number'])
    def send_number_choices(message):
        with SessionLocal() as session:
            # Получаем все доступные числа и их интерпретации
            number_choices = session.query(NumberChoice).all()

            # Разделяем числа на две категории
            left_column = [choice for choice in number_choices if choice.number < 10]  # Числа от 0 до 9
            right_column = [choice for choice in number_choices if choice.number >= 111]  # Числа от 111 до 999

            # Формируем сообщение и кнопки
            response_message = "Выберите цифровое значение:"
            markup = InlineKeyboardMarkup()

            # Сравниваем длину списков, чтобы избежать IndexError
            max_length = max(len(left_column), len(right_column))

            for i in range(max_length):
                # Берем элемент из левого столбца, если он существует
                left_button = InlineKeyboardButton(
                    text=str(left_column[i].number),
                    callback_data=f"choose_number:{left_column[i].id}"
                ) if i < len(left_column) else None

                # Берем элемент из правого столбца, если он существует
                right_button = InlineKeyboardButton(
                    text=str(right_column[i].number),
                    callback_data=f"choose_number:{right_column[i].id}"
                ) if i < len(right_column) else None

                # Добавляем кнопки в строку. Если обе кнопки существуют — добавляем их обе, если нет — только существующую
                row = [left_button] if left_button else []
                if right_button:
                    row.append(right_button)

                # Добавляем строку в разметку
                markup.row(*row)

            print(message.from_user.id, "id")
            # Отправляем сообщение с кнопками
            bot.send_message(message.chat.id, response_message, reply_markup=markup)

    @bot.message_handler(commands=['time_list'])
    def list_interpretations(message):
        user_id = message.from_user.id
        # if not is_user_subscribed(user_id, bot):
        #     response_message = (
        #         "Для использования этой команды подпишитесь на следующие каналы:\n"
        #         "- Αρτέμιος 𝚁𝙴𝚃𝚁𝙴𝙰𝚃𝚂\n"
        #         "- Вселяющий Веру Шаман"
        #     )
        #     bot.send_message(message.chat.id, response_message)
        #     return

        with SessionLocal() as session:
            time_choices = session.query(TimeChoice).all()  # Получаем все варианты выбора времени
            response = "<b>Трактовки времени:</b>\n\n"
            interpretations = {}

            for choice in time_choices:
                # Используем time_range вместо name
                if choice.time_range.time_range not in interpretations:
                    interpretations[choice.time_range.time_range] = {}
                interpretations[choice.time_range.time_range][choice.choice] = choice.interpretation

            for period, choices in interpretations.items():
                response += f"<b>{period}</b>\n"  # Используем time_range для заголовка
                for time, interpretation in choices.items():
                    # Экранирование спецсимволов для HTML
                    safe_time = time.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    safe_interpretation = interpretation.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    response += f"<b>{safe_time}</b>: {safe_interpretation}\n"
                response += "\n"  # Добавляем дополнительный перенос строки между периодами

            # Удалите пустые строки в конце ответа
            response = response.strip()

            send_long_message(bot, message.chat.id, response, parse_mode='HTML')

    @bot.message_handler(commands=['all_time_stat'])
    def stat_time_selections(message):
        with SessionLocal() as session:
            # Находим пользователя по tg_id
            user = session.query(User).filter_by(tg_id=message.chat.id).first()

            if not user:
                response = "Пользователь не найден."
                send_long_message(bot, message.chat.id, response, parse_mode='HTML')
                return

            # Получаем все выборы времени для данного пользователя
            time_selections = session.query(TimeSelection).filter_by(user_id=user.id).all()

            if not time_selections:
                response = "Вы ещё не добавляли время."
                send_long_message(bot, message.chat.id, response, parse_mode='HTML')
                return

            time_stats = defaultdict(int)

            # Собираем статистику по временам
            for selection in time_selections:
                # Увеличиваем счетчик для выбранного времени
                time_stats[selection.time_choice.choice] += 1

            # Сортируем статистику по количеству выборов (от большего к меньшему)
            sorted_time_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)

            # Формируем ответ с трактовками
            response = "<b>Статистика временных знаков:</b>\n\n"
            for time_choice, count in sorted_time_stats:
                # Получаем трактовку времени
                interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
                if interpretation:
                    response += f"<b>{time_choice}</b>: {count} раз(а) - {interpretation.interpretation}\n"

            # Удалите пустые строки в конце ответа
            response = response.strip()

            send_long_message(bot, message.chat.id, response, parse_mode='HTML')

    @bot.message_handler(commands=['stat_range'])
    def stat_time_range(message):
        user_id = message.chat.id
        # Устанавливаем новое состояние, ожидаем выбора предопределённого диапазона
        set_user_state(user_id, STATE_AWAITING_PREDEFINED_RANGE)
        config_instance.logger.info("stat_range")
        # Создаём инлайн-клавиатуру
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_this_week = InlineKeyboardButton(text="Эта неделя", callback_data="stat_range_this_week")
        btn_last_week = InlineKeyboardButton(text="Прошлая неделя", callback_data="stat_range_last_week")
        btn_this_month = InlineKeyboardButton(text="Этот месяц", callback_data="stat_range_this_month")
        btn_calendar = InlineKeyboardButton(text="Календарь", callback_data="stat_range_calendar")

        # Добавляем кнопки в клавиатуру
        keyboard.add(btn_this_week, btn_last_week, btn_this_month, btn_calendar)

        # Отправляем сообщение с инлайн-кнопками
        bot.send_message(user_id, "Выберите временной промежуток для статистики:", reply_markup=keyboard)
