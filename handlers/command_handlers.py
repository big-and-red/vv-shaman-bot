import logging
from collections import defaultdict
from datetime import datetime

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config_instance
from db_helpers.models import SessionLocal, TimeChoice, TimeRange, TimeSelection, User, NumberChoice
from data_interpretations.time_interpretations import time_interpretations
from states import set_user_state, STATE_AWAITING_START_DATE, STATE_AWAITING_PREDEFINED_RANGE, STATE_AWAITING_STAT_TYPE
from utils.inline_calendar import TelegramCalendar
from utils.message_utils import generate_time_range_buttons
from utils.message_utils import send_long_message
from utils.stat_utils import get_user_time_statistics
from utils.sub_channel_checker import is_user_subscribed

calendar_instance = TelegramCalendar(locale="ru")
# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def register_command_handlers(bot: TeleBot):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        logger.info("————— /start —————")
        with SessionLocal() as session:
            user = session.query(User).filter_by(tg_id=message.from_user.id).first()
            if not user:
                user = User(username=message.from_user.username, tg_id=message.from_user.id)
                session.add(user)  # Добавляем пользователя в сессию, если он новый
                session.commit()

        response_message = (
            "Этот бот поможет тебе записывать знаки Вселенной.\n\n"
            "<b>Всякий раз, когда ты видишь время, определенное сочетание цифр — это подсказка.</b>\n"
            "Если на протяжении долгого времени тебе раз за разом попадается одно и то же время, минимум 3 раза"
            "— это подсказка прямо в лоб.\n\n"
            "<b>Команды</b>\n"
            "<b>/time</b> — Добавить временной знак.\n"
            "<b>/number</b> — Добавить числовой знак.\n"
            "<b>/stat_range</b> — Посмотреть статистику в промежутке (время/числа).\n"
            "<b>/all_stat</b> — Общая статистика (время/числа).\n"
            "<b>/list</b> — Полный список временных знаков (время/числа).\n\n"
            "Подписывайтесь на открытые каналы:\n"
            "<a href='https://t.me/strong_mvp'>Артём ВВШ</a>\n"
            "<a href='https://t.me/arsenmarkarian'>Главком</a>\n\n"
            "Автор бота — <a href='https://t.me/smthng_hero'>Leon</a>"
        )
        bot.send_message(message.chat.id, response_message, parse_mode="HTML", disable_web_page_preview=True)

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

    @bot.message_handler(commands=['list'])
    def list_command(message):
        markup = InlineKeyboardMarkup()
        time_button = InlineKeyboardButton("Время", callback_data="list_time")
        numbers_button = InlineKeyboardButton("Числа", callback_data="list_numbers")
        markup.add(time_button, numbers_button)

        bot.send_message(
            message.chat.id,
            "Выберите что хотите посмотреть:",
            reply_markup=markup
        )

    @bot.message_handler(commands=['all_stat'])
    def all_stat_command(message):
        markup = InlineKeyboardMarkup()
        time_button = InlineKeyboardButton("Время", callback_data="all_stat_time")
        numbers_button = InlineKeyboardButton("Числа", callback_data="all_stat_numbers")
        markup.add(time_button, numbers_button)

        bot.send_message(
            message.chat.id,
            "Выберите тип статистики:",
            reply_markup=markup
        )

    @bot.message_handler(commands=['stat_range'])
    def stat_time_range(message):
        user_id = message.chat.id
        set_user_state(user_id, STATE_AWAITING_STAT_TYPE)

        # Создаём клавиатуру для выбора типа статистики
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_time = InlineKeyboardButton(text="Время", callback_data="stat_type_time")
        btn_numbers = InlineKeyboardButton(text="Числа", callback_data="stat_type_numbers")

        keyboard.add(btn_time, btn_numbers)

        bot.send_message(user_id, "Выберите тип статистики:", reply_markup=keyboard)