from collections import defaultdict
from datetime import datetime, timedelta

from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config_instance
from db_helpers.models import User, TimeSelection, SessionLocal, TimeChoice, TimeRange, NumberSelection, NumberChoice
from data_interpretations.time_interpretations import time_interpretations
from handlers.command_handlers import calendar_instance
from states import clear_user_state, STATE_AWAITING_END_DATE, set_user_state, STATE_AWAITING_START_DATE, get_user_state, \
    STATE_AWAITING_PREDEFINED_RANGE, STATE_AWAITING_STAT_TYPE
from utils.message_utils import generate_time_choice_buttons, generate_time_range_buttons, send_long_message
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
        # Правильное разделение данных
        try:
            time_range_id, time_choice_id = call.data.split('_')[
                                            1:]  # Используем split('_') и берем два последних элемента
        except ValueError:
            bot.send_message(call.message.chat.id, "Неверный формат данных")
            return

        with SessionLocal() as session:
            try:
                # Получаем интерпретацию для выбранного времени
                time_choice = session.query(TimeChoice).filter_by(id=time_choice_id).first()

                # Проверка существования time_choice
                if time_choice is None:
                    bot.send_message(call.message.chat.id, "Выбор времени не найден.")
                    return

                interpretation = time_choice.interpretation

                # Получение или создание пользователя
                user = session.query(User).filter_by(tg_id=str(call.from_user.id)).first()
                if not user:
                    user = User(
                        username=call.from_user.username or "Unknown",  # Обработка случая отсутствия username
                        tg_id=str(call.from_user.id)
                    )
                    session.add(user)
                    session.flush()  # Получаем id пользователя до создания time_selection

                # Создаём запись выбора времени
                time_selection = TimeSelection(
                    time_choice_id=time_choice.id,
                    user_id=user.id
                )
                session.add(time_selection)

                # Создаем клавиатуру
                markup = InlineKeyboardMarkup()
                add_more_button = InlineKeyboardButton("Добавить ещё", callback_data='add_more')
                markup.add(add_more_button)

                # Отправляем сообщение
                bot.send_message(
                    call.message.chat.id,
                    f"*{time_choice.choice}*: {interpretation}",
                    parse_mode='Markdown',  # Добавлен parse_mode
                    reply_markup=markup
                )

                session.commit()

            except Exception as e:
                session.rollback()
                bot.send_message(call.message.chat.id, "Произошла ошибка при обработке выбора.")
                print(f"Error in process_time_choice: {e}")  # Логирование ошибки

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
                    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

                    # Логируем начальную и конечную даты
                    print(
                        f"Начальная дата: {start_date.strftime('%Y-%m-%d')}, Конечная дата: {end_date.strftime('%Y-%m-%d')}")

                    # Если конечная дата меньше начальной, меняем их местами
                    if end_date < start_date:
                        start_date, end_date = end_date, start_date

                    # Вызываем функцию для получения статистики за промежуток
                    stat_type = get_user_state(user_id).get('stat_type')
                    response = fetch_stat_for_time_range(call.message, start_date, end_date, stat_type)

                    # Очищаем состояние
                    clear_user_state(user_id)
                    bot.send_message(call.message.chat.id, response) # parse_mode

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith("stat_range_"))
    def handle_range_callback(call):
        user_id = call.message.chat.id
        state = get_user_state(user_id)

        bot.answer_callback_query(call.id)

        if not state or state.get('state') != STATE_AWAITING_PREDEFINED_RANGE:
            bot.send_message(user_id, "Пожалуйста, начните заново командой /stat_range.")
            return

        stat_type = state.get('stat_type', 'time')  # По умолчанию время
        callback_data = call.data
        now = datetime.now()

        if callback_data == "stat_range_this_week":
            start_of_week = now - timedelta(days=now.weekday())
            end_of_week = now
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif callback_data == "stat_range_last_week":
            start_of_week = now - timedelta(days=now.weekday() + 7)
            end_of_week = start_of_week + timedelta(days=6)
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif callback_data == "stat_range_this_month":
            start_of_week = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_week = now
            end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)

        elif callback_data == "stat_range_calendar":
            set_user_state(user_id, STATE_AWAITING_START_DATE, {'stat_type': stat_type})
            calendar_markup = calendar_instance.create_calendar(now.year, now.month)
            bot.send_message(user_id, "Выберите начальную дату:", reply_markup=calendar_markup)
            return
        else:
            bot.send_message(user_id, "Неизвестный выбор. Пожалуйста, попробуйте снова.")
            return
        stat_type = get_user_state(user_id).get('stat_type')
        response = fetch_stat_for_time_range(call.message, start_of_week, end_of_week, stat_type)
        clear_user_state(user_id)
        bot.send_message(user_id, response) # parse_mode

    @bot.callback_query_handler(func=lambda call: call.data.startswith("stat_type_"))
    def handle_stat_type_selection(call):
        user_id = call.message.chat.id
        state = get_user_state(user_id)

        bot.answer_callback_query(call.id)

        if not state or state.get('state') != STATE_AWAITING_STAT_TYPE:
            bot.send_message(user_id, "Пожалуйста, начните заново командой /stat_range.")
            return

        # Сохраняем выбранный тип статистики
        stat_type = call.data.replace("stat_type_", "")
        print(stat_type)
        set_user_state(user_id, STATE_AWAITING_PREDEFINED_RANGE, {'stat_type': stat_type})

        # Создаём инлайн-клавиатуру для выбора периода
        keyboard = InlineKeyboardMarkup(row_width=2)
        btn_this_week = InlineKeyboardButton(text="Эта неделя", callback_data="stat_range_this_week")
        btn_last_week = InlineKeyboardButton(text="Прошлая неделя", callback_data="stat_range_last_week")
        btn_this_month = InlineKeyboardButton(text="Этот месяц", callback_data="stat_range_this_month")
        btn_calendar = InlineKeyboardButton(text="Календарь", callback_data="stat_range_calendar")

        keyboard.add(btn_this_week, btn_last_week, btn_this_month, btn_calendar)

        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text="Выберите временной промежуток для статистики:",
            reply_markup=keyboard
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("choose_number:"))
    def handle_number_choice(call):
        # Получаем ID выбранного числа из callback_data
        number_choice_id = int(call.data.split(":")[1])

        with SessionLocal() as session:
            # Получаем выбранное число и его интерпретацию
            number_choice = session.query(NumberChoice).filter_by(id=number_choice_id).first()

            if number_choice is None:
                bot.send_message(call.message.chat.id, "Неверный выбор.")
                return

            # Предположим, что `user_id` можно получить из call.message.from_user.id
            user_id = call.from_user.id
            print(user_id)

            # Проверяем, существует ли пользователь
            user = session.query(User).filter_by(tg_id=user_id).first()
            print(user)
            if user is None:
                # Если пользователя нет, можно вернуть ошибку или создать пользователя
                bot.send_message(call.message.chat.id, "Пользователь не найден.")
                return

            # Создаем новую запись в таблице number_selections
            new_selection = NumberSelection(
                user_id=user.id,
                number_choice_id=number_choice.id
            )
            session.add(new_selection)
            session.commit()

            # Отправляем пользователю интерпретацию выбранного числа
            response_message = f"Вы выбрали число *{number_choice.number}*.\n\n*Интерпретация:* \n{number_choice.interpretation}"
            bot.send_message(call.message.chat.id, response_message) # parse_mode


    @bot.callback_query_handler(func=lambda call: call.data.startswith("all_stat_"))
    def handle_all_stat_selection(call):
        stat_type = call.data.replace("all_stat_", "")

        with SessionLocal() as session:
            user = session.query(User).filter_by(tg_id=call.message.chat.id).first()

            if not user:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Пользователь не найден.",
                    # parse_mode
                )
                return

            if stat_type == "time":
                # Получаем все выборы времени для данного пользователя
                time_selections = session.query(TimeSelection).filter_by(user_id=user.id).all()

                if not time_selections:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="Вы ещё не добавляли время.",
                        # parse_mode='Markdown'
                    )
                    return

                time_stats = defaultdict(int)
                for selection in time_selections:
                    time_stats[selection.time_choice.choice] += 1

                sorted_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)
                response = "*Статистика временных знаков за все время:*\n\n"

                for time_choice, count in sorted_stats:
                    interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
                    if interpretation:
                        response += f"*{time_choice}*: {count} раз(а) - {interpretation.interpretation}\n\n"

            elif stat_type == "numbers":
                # Получаем все выборы чисел для данного пользователя
                number_selections = session.query(NumberSelection).filter_by(user_id=user.id).all()

                if not number_selections:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="Вы ещё не добавляли числа.",
                        # parse_mode='Markdown'
                    )
                    return

                number_stats = defaultdict(int)
                for selection in number_selections:
                    number_stats[selection.number_choice.number] += 1

                sorted_stats = sorted(number_stats.items(), key=lambda x: x[1], reverse=True)
                response = "*Статистика чисел за все время:*\n\n"

                for number, count in sorted_stats:
                    interpretation = session.query(NumberChoice).filter_by(number=number).first()
                    if interpretation:
                        response += f"*{number}*: {count} раз(а) - {interpretation.interpretation}\n\n"

            response = response.strip()
            send_long_message(bot, call.message.chat.id, response)  # parse_mode

    @bot.callback_query_handler(func=lambda call: call.data.startswith("list_"))
    def handle_list_selection(call):
        list_type = call.data.replace("list_", "")

        with SessionLocal() as session:
            if list_type == "time":
                time_choices = session.query(TimeChoice).all()
                response = "*Трактовки времени:*\n\n"
                interpretations = {}

                for choice in time_choices:
                    if choice.time_range.time_range not in interpretations:
                        interpretations[choice.time_range.time_range] = {}
                    interpretations[choice.time_range.time_range][choice.choice] = choice.interpretation

                for period, choices in interpretations.items():
                    response += f"*{period}*\n"
                    for time, interpretation in choices.items():
                        safe_time = time.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        safe_interpretation = interpretation.replace('&', '&amp;').replace('<', '&lt;').replace('>',
                                                                                                                '&gt;')
                        response += f"*{safe_time}*: {safe_interpretation}\n"
                    response += "\n"

            elif list_type == "numbers":
                number_choices = session.query(NumberChoice).all()
                response = "*Трактовки чисел:*\n\n"

                for choice in number_choices:
                    safe_number = str(choice.number).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    safe_interpretation = choice.interpretation.replace('&', '&amp;').replace('<', '&lt;').replace('>',
                                                                                                                   '&gt;')
                    response += f"*{safe_number}*: {safe_interpretation}\n\n"

            response = response.strip()
            send_long_message(bot, call.message.chat.id, response) # parse_mode
