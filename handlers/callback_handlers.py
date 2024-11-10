from datetime import datetime

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from db_helpers.models import User, TimeSelection, SessionLocal, TimeChoice, TimeRange
from data_interpretations.time_interpretations import time_interpretations
from handlers.command_handlers import calendar_instance
from states import clear_user_state, STATE_AWAITING_END_DATE, set_user_state, STATE_AWAITING_START_DATE, get_user_state
from utils.message_utils import generate_time_choice_buttons, generate_time_range_buttons
from utils.stat_utils import fetch_stat_for_time_range


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

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("day_", "prev_", "next_")))
    def handle_calendar_callback(call):
        user_id = call.message.chat.id
        state = get_user_state(user_id)

        bot.answer_callback_query(call.id)

        # Извлекаем текущий год и месяц из состояния пользователя, если они есть
        current_year = state.get("year", datetime.now().year)
        current_month = state.get("month", datetime.now().month)

        print(f"Текущий год: {current_year}, Текущий месяц: {current_month}")

        # Обрабатываем коллбэки календаря
        calendar_response = calendar_instance.handle_callback(call.data, current_year, current_month)

        if not calendar_response:
            print("Ошибка: Не удалось обработать коллбэк календаря.")
            return

        # Если выбран день
        if calendar_response[2] is not None:
            day = calendar_response[2]

            # Проверяем, если состояние было изменено при переключении месяца
            # Обновляем year и month из состояния, если они обновлялись
            current_year = state.get("year", current_year)
            current_month = state.get("month", current_month)

            selected_date = datetime(current_year, current_month, day)
            print(f"Выбранная дата: {selected_date.strftime('%Y-%m-%d')}")

            if state and state["state"] == STATE_AWAITING_START_DATE:
                # Устанавливаем начальную дату и переходим к выбору конечной
                set_user_state(user_id, STATE_AWAITING_END_DATE,
                               {"start_date": selected_date, "year": current_year, "month": current_month})
                bot.send_message(user_id, f"Начальная дата выбрана: {selected_date.strftime('%Y-%m-%d')}")
                bot.send_message(user_id, "Теперь выберите конечную дату:")

                # Показываем календарь для конечной даты
                calendar_markup = calendar_instance.create_calendar(current_year, current_month)
                bot.send_message(user_id, "Выберите конечную дату:", reply_markup=calendar_markup)

            elif state and state["state"] == STATE_AWAITING_END_DATE:
                # Получаем начальную дату из состояния
                start_date = state.get("start_date")
                if start_date:
                    end_date = selected_date

                    # Логируем начальную и конечную даты
                    print(
                        f"Начальная дата: {start_date.strftime('%Y-%m-%d')}, Конечная дата: {end_date.strftime('%Y-%m-%d')}")

                    # Если конечная дата меньше начальной, меняем их местами
                    if end_date < start_date:
                        start_date, end_date = end_date, start_date

                    # Вызываем функцию для получения статистики за промежуток
                    response = fetch_stat_for_time_range(call.message, start_date, end_date)

                    # Очищаем состояние
                    clear_user_state(user_id)
                    bot.send_message(call.message.chat.id, response, parse_mode='HTML')

        # Если переключается месяц
        elif calendar_response[0] is not None or calendar_response[1] is not None:
            new_year, new_month = calendar_response[0], calendar_response[1]

            if new_year is not None and new_month is not None:
                print(f"Переключено на: {new_year}, {new_month}")

                # Получаем текущие данные состояния пользователя
                state_data = get_user_state(user_id) or {}

                # Обновляем только 'year' и 'month' в данных состояния
                state_data['year'] = new_year
                state_data['month'] = new_month

                # Обновляем состояние пользователя, сохраняя остальные данные
                set_user_state(user_id, state_data.get('state', state["state"]), state_data)

                # Создаем новый календарь с обновленным месяцем
                new_calendar_markup = calendar_instance.create_calendar(new_year, new_month)

                # Обновляем клавиатуру в сообщении
                try:
                    bot.edit_message_reply_markup(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        reply_markup=new_calendar_markup
                    )
                    print(f"Сообщение обновлено для {new_year}-{new_month}")
                except Exception as e:
                    print(f"Ошибка при обновлении сообщения: {str(e)}")
            else:
                print("Ошибка: неверные значения года или месяца при переключении.")
