from collections import defaultdict
from datetime import datetime

from telebot import TeleBot

from db_helpers.models import SessionLocal, TimeChoice, TimeRange, TimeSelection, User
from data_interpretations.time_interpretations import time_interpretations
from states import set_user_state, STATE_AWAITING_START_DATE
from utils.inline_calendar import TelegramCalendar
from utils.message_utils import generate_time_range_buttons
from utils.message_utils import send_long_message
from utils.stat_utils import get_user_time_statistics
from utils.sub_channel_checker import is_user_subscribed

calendar_instance = TelegramCalendar(locale="ru")


def register_command_handlers(bot: TeleBot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        with SessionLocal() as session:
            user = session.query(User).filter_by(tg_id=message.from_user.id).first()
            if not user:
                user = User(username=message.from_user.username, tg_id=str(message.from_user.id))
                session.add(user)  # Добавляем пользователя в сессию, если он новый
                session.commit()

        response_message = (
            "Этот бот поможет тебе записывать знаки Вселенной.\n\n"
            "*Всякий раз, когда ты видишь время, определенное сочетание цифр — это подсказка.*\n"
            "Если на протяжении долгого времени тебе раз за разом попадается одно и то же время, минимум 3 раза, "
            "— это подсказка прямо в лоб.\n\n"
            "*Команды*\n"
            "*/time* — Добавить временной знак.\n"
            "*/stat* — Твоя статистика.\n"
            "*/list* — Полный список временных знаков.\n\n"
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

    @bot.message_handler(commands=['list'])
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

    @bot.message_handler(commands=['stat'])
    def stat_time_selections(message):
        with SessionLocal() as session:
            # Находим пользователя по tg_id
            user = session.query(User).filter_by(tg_id=message.chat.id).first()
            print(user.id)
            print(user.tg_id)
            print('*' * 15)

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
        # Устанавливаем состояние для пользователя
        set_user_state(message.chat.id, STATE_AWAITING_START_DATE)

        now = datetime.now()
        calendar_markup = calendar_instance.create_calendar(now.year, now.month)
        bot.send_message(message.chat.id, "Выберите начальную дату:", reply_markup=calendar_markup)
