from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from db_helpers.models import User, TimeSelection, SessionLocal, TimeChoice, TimeRange
from time_data.time_interpretations import time_interpretations
from utils.message_utils import generate_time_choice_buttons, generate_time_range_buttons


def register_callback_handlers(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('range_'))
    def process_time_range(call):
        time_range_id = call.data.split('_')[1]  # Получаем id временного промежутка
        with SessionLocal() as session:
            time_choices = session.query(TimeChoice).filter_by(
                time_range_id=time_range_id).all()  # Получаем временные варианты

        if time_choices:
            markup = generate_time_choice_buttons(time_choices)  # Создаем кнопки для выбора времени
            bot.send_message(call.message.chat.id, "Выберите время:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Временные варианты не найдены.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
    def process_time_choice(call):
        time_range_id, time_choice_id = call.data.split('_')[1], call.data.split('_')[2]

        with SessionLocal() as session:  # Открываем сессию
            # Получаем интерпретацию для выбранного времени
            time_choice = session.query(TimeChoice).filter_by(id=time_choice_id).first()

            # Проверка, что time_choice существует
            if time_choice is None:
                bot.send_message(call.message.chat.id, "Выбор времени не найден.")
                return

            interpretation = time_choice.interpretation  # Получаем интерпретацию

            # Запись выбора пользователя в базу данных
            user = session.query(User).filter_by(tg_id=call.from_user.id).first()
            if not user:
                user = User(username=call.from_user.username, tg_id=str(call.from_user.id))
                session.add(user)  # Добавляем пользователя в сессию, если он новый
                session.commit()

            # Создаём запись в таблице time_selections
            time_selection = TimeSelection(time_choice_id=time_choice.id,
                                           user_id=user.id)  # Используем id выбранного времени
            session.add(time_selection)  # Добавляем выбор времени в сессию

            markup = InlineKeyboardMarkup()
            add_more_button = InlineKeyboardButton("Добавить ещё", callback_data='add_more')
            markup.add(add_more_button)
            # Отправляем интерпретацию выбора

            bot.send_message(call.message.chat.id, f"*{time_choice.choice}*: {interpretation}", parse_mode="Markdown",
                             reply_markup=markup)

            session.commit()

    @bot.callback_query_handler(func=lambda call: call.data in ['back', 'add_more'])
    def go_back_or_add_more(call):
        with SessionLocal() as session:  # Открываем сессию
            # Получаем все временные промежутки
            time_ranges = session.query(TimeRange).all()

        if time_ranges:
            # Генерируем кнопки для выбора временного промежутка
            markup = generate_time_range_buttons(
                time_ranges)  # Убедитесь, что функция принимает список временных промежутков
            bot.send_message(call.message.chat.id, "Выберите временной промежуток:", reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, "Временные промежутки не найдены.")
