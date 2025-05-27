import uuid
import logging
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

# Настройка логирования
logger = logging.getLogger(__name__)


def register_callback_handlers(bot: TeleBot):
    @bot.callback_query_handler(func=lambda call: call.data.startswith('range_'))
    def process_time_range(call):
        try:
            time_range_id = call.data.split('_')[1]  # Получаем id временного промежутка
            logger.info(f"Выбран временной промежуток: {time_range_id}, пользователь: {call.from_user.id}")

            with SessionLocal() as session:
                time_choices = session.query(TimeChoice).filter_by(
                    time_range_id=time_range_id).all()  # Получаем временные варианты

            if time_choices:
                markup = generate_time_choice_buttons(time_choices)  # Создаем кнопки для выбора времени
                bot.send_message(call.message.chat.id, "Выберите время:", reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, "Временные варианты не найдены.")
                logger.warning(f"Не найдены временные варианты для промежутка {time_range_id}")
        except Exception as e:
            logger.error(f"Ошибка в process_time_range: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке запроса.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('time_'))
    def process_time_choice(call):
        try:
            parts = call.data.split('_')
            if len(parts) < 3:
                bot.send_message(call.message.chat.id, "Неверный формат данных")
                logger.error(f"Неверный формат данных в process_time_choice: {call.data}")
                return

            time_range_id, time_choice_id = parts[1:]
            logger.info(f"Выбрано время: {time_choice_id}, пользователь: {call.from_user.id}")

            with SessionLocal() as session:
                time_choice = session.query(TimeChoice).filter_by(id=time_choice_id).first()

                if time_choice is None:
                    bot.send_message(call.message.chat.id, "Выбор времени не найден.")
                    logger.warning(f"Выбор времени не найден: {time_choice_id}")
                    return

                interpretation = time_choice.interpretation

                # Используем int для tg_id, так как в модели User это Integer
                user = session.query(User).filter_by(tg_id=call.from_user.id).first()
                if not user:
                    user = User(
                        username=call.from_user.username or "Unknown",
                        tg_id=call.from_user.id
                    )
                    session.add(user)
                    session.flush()
                    logger.info(f"Создан новый пользователь: {user.id}, tg_id: {user.tg_id}")

                # Создаём запись выбора времени с явным указанием UUID
                time_selection = TimeSelection(
                    id=uuid.uuid4(),  # Явно указываем UUID
                    time_choice_id=time_choice.id,
                    user_id=user.id
                )
                session.add(time_selection)

                markup = InlineKeyboardMarkup()
                add_more_button = InlineKeyboardButton("Добавить ещё", callback_data='add_more')
                markup.add(add_more_button)

                bot.send_message(
                    call.message.chat.id,
                    f"<b>{time_choice.choice}</b>: {interpretation}",
                    parse_mode='HTML',
                    reply_markup=markup
                )

                session.commit()
                logger.info(f"Сохранен выбор времени: {time_choice.choice} для пользователя {user.id}")

        except Exception as e:
            logger.error(f"Ошибка в process_time_choice: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке выбора.")

    @bot.callback_query_handler(func=lambda call: call.data in ['back', 'add_more'])
    def go_back_or_add_more(call):
        try:
            logger.info(f"Пользователь {call.from_user.id} выбрал {call.data}")
            with SessionLocal() as session:
                time_ranges = session.query(TimeRange).all()

            if time_ranges:
                markup = generate_time_range_buttons(time_ranges)
                bot.send_message(call.message.chat.id, "Выберите временной промежуток:", reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, "Временные промежутки не найдены.")
                logger.warning("Временные промежутки не найдены в БД")
        except Exception as e:
            logger.error(f"Ошибка в go_back_or_add_more: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке запроса.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("day_", "prev_", "next_")))
    def handle_calendar_callback(call):
        try:
            user_id = call.message.chat.id
            state = get_user_state(user_id) or {}

            logger.info(f"Календарный колбэк: {call.data}, пользователь: {user_id}, состояние: {state}")
            bot.answer_callback_query(call.id)

            # Извлекаем текущий год и месяц из состояния пользователя, если они есть
            current_year = state.get("year", datetime.now().year)
            current_month = state.get("month", datetime.now().month)

            # Обрабатываем коллбэки календаря
            calendar_response = calendar_instance.handle_callback(call.data, current_year, current_month)

            if not calendar_response:
                logger.error("Не удалось обработать коллбэк календаря.")
                bot.send_message(user_id, "Произошла ошибка при работе с календарем.")
                return

            # Если выбран день
            if calendar_response[2] is not None:
                day = calendar_response[2]
                year, month = calendar_response[0], calendar_response[1]

                selected_date = datetime(year, month, day)
                logger.info(f"Выбрана дата: {selected_date.strftime('%Y-%m-%d')}")

                if not state:
                    logger.warning(f"Состояние отсутствует для пользователя {user_id}")
                    bot.send_message(user_id, "Пожалуйста, начните выбор даты заново.")
                    return

                if state.get("state") == STATE_AWAITING_START_DATE:
                    # Устанавливаем начальную дату и переходим к выбору конечной
                    set_user_state(user_id, STATE_AWAITING_END_DATE,
                                   {"start_date": selected_date, "year": year, "month": month,
                                    "stat_type": state.get("stat_type")})
                    bot.send_message(user_id, f"Начальная дата выбрана: {selected_date.strftime('%Y-%m-%d')}")
                    bot.send_message(user_id, "Теперь выберите конечную дату:")

                    # Показываем календарь для конечной даты
                    calendar_markup = calendar_instance.create_calendar(year, month)
                    bot.send_message(user_id, "Выберите конечную дату:", reply_markup=calendar_markup)

                elif state.get("state") == STATE_AWAITING_END_DATE:
                    # Получаем начальную дату из состояния
                    start_date = state.get("start_date")
                    if start_date:
                        end_date = selected_date
                        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

                        # Если конечная дата меньше начальной, меняем их местами
                        if end_date < start_date:
                            logger.info(f"Конечная дата {end_date} меньше начальной {start_date}, меняем местами")
                            start_date, end_date = end_date, start_date

                        # Вызываем функцию для получения статистики за промежуток
                        stat_type = state.get('stat_type', 'time')
                        logger.info(f"Запрос статистики за период {start_date} - {end_date}, тип: {stat_type}")
                        response = fetch_stat_for_time_range(call.message, start_date, end_date, stat_type)

                        # Очищаем состояние и отправляем результат
                        clear_user_state(user_id)
                        bot.send_message(user_id, response, parse_mode='HTML')
                    else:
                        logger.error(f"Начальная дата не найдена в состоянии пользователя {user_id}")
                        bot.send_message(user_id, "Ошибка: начальная дата не найдена. Пожалуйста, начните заново.")
                        clear_user_state(user_id)
                else:
                    logger.warning(f"Неожиданное состояние для пользователя {user_id}: {state}")
                    bot.send_message(user_id, "Пожалуйста, начните процесс выбора даты заново.")
                    clear_user_state(user_id)

            # Если переключается месяц
            elif calendar_response[0] is not None and calendar_response[1] is not None:
                new_year, new_month = calendar_response[0], calendar_response[1]
                logger.info(f"Переключение календаря на {new_year}-{new_month}")

                # Обновляем год и месяц в состоянии пользователя
                state_data = state.copy() if state else {}
                state_data['year'] = new_year
                state_data['month'] = new_month

                # Сохраняем обновленное состояние
                current_state = state_data.get('state', STATE_AWAITING_START_DATE)
                set_user_state(user_id, current_state, state_data)

                # Создаем новый календарь с обновленным месяцем
                new_calendar_markup = calendar_instance.create_calendar(new_year, new_month)

                # Обновляем клавиатуру в сообщении
                try:
                    bot.edit_message_reply_markup(
                        chat_id=user_id,
                        message_id=call.message.message_id,
                        reply_markup=new_calendar_markup
                    )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении календаря: {e}")
                    bot.send_message(user_id,
                                     "Произошла ошибка при обновлении календаря. Пожалуйста, попробуйте снова.")
        except Exception as e:
            logger.error(f"Ошибка в handle_calendar_callback: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при работе с календарем.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("stat_range_"))
    def handle_range_callback(call):
        try:
            user_id = call.message.chat.id
            state = get_user_state(user_id)
            logger.info(f"Выбран диапазон статистики: {call.data}, пользователь: {user_id}")

            bot.answer_callback_query(call.id)

            if not state or state.get('state') != STATE_AWAITING_PREDEFINED_RANGE:
                bot.send_message(user_id, "Пожалуйста, начните заново командой /stat_range.")
                logger.warning(f"Неправильное состояние для stat_range: {state}")
                return

            stat_type = state.get('stat_type', 'time')  # По умолчанию время
            callback_data = call.data
            now = datetime.now()

            if callback_data == "stat_range_this_week":
                start_of_week = now - timedelta(days=now.weekday())
                end_of_week = now
                start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Выбрана текущая неделя: {start_of_week} - {end_of_week}")

            elif callback_data == "stat_range_last_week":
                start_of_week = now - timedelta(days=now.weekday() + 7)
                end_of_week = start_of_week + timedelta(days=6)
                start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Выбрана прошлая неделя: {start_of_week} - {end_of_week}")

            elif callback_data == "stat_range_this_month":
                start_of_week = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_of_week = now
                end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
                logger.info(f"Выбран текущий месяц: {start_of_week} - {end_of_week}")

            elif callback_data == "stat_range_calendar":
                set_user_state(user_id, STATE_AWAITING_START_DATE, {'stat_type': stat_type})
                calendar_markup = calendar_instance.create_calendar(now.year, now.month)
                bot.send_message(user_id, "Выберите начальную дату:", reply_markup=calendar_markup)
                logger.info(f"Выбор через календарь для пользователя {user_id}")
                return
            else:
                bot.send_message(user_id, "Неизвестный выбор. Пожалуйста, попробуйте снова.")
                logger.warning(f"Неизвестный диапазон статистики: {callback_data}")
                return

            response = fetch_stat_for_time_range(call.message, start_of_week, end_of_week, stat_type)
            clear_user_state(user_id)
            bot.send_message(user_id, response, parse_mode='HTML')
            logger.info(f"Отправлена статистика за период для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка в handle_range_callback: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке запроса статистики.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("stat_type_"))
    def handle_stat_type_selection(call):
        try:
            user_id = call.message.chat.id
            state = get_user_state(user_id)
            logger.info(f"Выбран тип статистики: {call.data}, пользователь: {user_id}")

            bot.answer_callback_query(call.id)

            if not state or state.get('state') != STATE_AWAITING_STAT_TYPE:
                bot.send_message(user_id, "Пожалуйста, начните заново командой /stat_range.")
                logger.warning(f"Неправильное состояние для stat_type: {state}")
                return

            # Сохраняем выбранный тип статистики
            stat_type = call.data.replace("stat_type_", "")
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
            logger.info(f"Запрошен выбор промежутка для типа {stat_type}")
        except Exception as e:
            logger.error(f"Ошибка в handle_stat_type_selection: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при выборе типа статистики.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("choose_number:"))
    def handle_number_choice(call):
        try:
            # Получаем ID выбранного числа из callback_data
            number_choice_id = int(call.data.split(":")[1])
            logger.info(f"Выбрано число ID: {number_choice_id}, пользователь: {call.from_user.id}")

            with SessionLocal() as session:
                # Получаем выбранное число и его интерпретацию
                number_choice = session.query(NumberChoice).filter_by(id=number_choice_id).first()

                if number_choice is None:
                    bot.send_message(call.message.chat.id, "Неверный выбор.")
                    logger.warning(f"Число с ID {number_choice_id} не найдено")
                    return

                # Получаем пользователя
                user_id = call.from_user.id
                user = session.query(User).filter_by(tg_id=user_id).first()

                if user is None:
                    # Создаем нового пользователя
                    user = User(
                        username=call.from_user.username or "Unknown",
                        tg_id=user_id
                    )
                    session.add(user)
                    session.flush()
                    logger.info(f"Создан новый пользователь: {user.id}, tg_id: {user.tg_id}")

                # Создаем новую запись в таблице number_selections
                new_selection = NumberSelection(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    number_choice_id=number_choice.id
                )
                session.add(new_selection)
                session.commit()
                logger.info(f"Сохранен выбор числа {number_choice.number} для пользователя {user.id}")

                # Отправляем пользователю интерпретацию выбранного числа
                response_message = f"Вы выбрали число <b>{number_choice.number}</b>.\n\n<b>Интерпретация:</b> \n{number_choice.interpretation}"
                bot.send_message(call.message.chat.id, response_message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Ошибка в handle_number_choice: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при обработке выбора числа.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("all_stat_"))
    def handle_all_stat_selection(call):
        try:
            stat_type = call.data.replace("all_stat_", "")
            logger.info(f"Запрошена полная статистика типа {stat_type}, пользователь: {call.from_user.id}")

            with SessionLocal() as session:
                user = session.query(User).filter_by(tg_id=call.message.chat.id).first()

                if not user:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="Пользователь не найден."
                    )
                    logger.warning(f"Пользователь не найден: {call.message.chat.id}")
                    return

                if stat_type == "time":
                    # Получаем все выборы времени для данного пользователя
                    time_selections = session.query(TimeSelection).filter_by(user_id=user.id).all()

                    if not time_selections:
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text="Вы ещё не добавляли время."
                        )
                        logger.info(f"Нет временных выборов для пользователя {user.id}")
                        return

                    time_stats = defaultdict(int)
                    for selection in time_selections:
                        time_stats[selection.time_choice.choice] += 1

                    sorted_stats = sorted(time_stats.items(), key=lambda x: x[1], reverse=True)
                    response = "<b>Статистика временных знаков за все время:</b>\n\n"

                    for time_choice, count in sorted_stats:
                        interpretation = session.query(TimeChoice).filter_by(choice=time_choice).first()
                        if interpretation:
                            response += f"<b>{time_choice}</b>: {count} раз(а) - {interpretation.interpretation}\n\n"

                elif stat_type == "numbers":
                    # Получаем все выборы чисел для данного пользователя
                    number_selections = session.query(NumberSelection).filter_by(user_id=user.id).all()

                    if not number_selections:
                        bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text="Вы ещё не добавляли числа."
                        )
                        logger.info(f"Нет числовых выборов для пользователя {user.id}")
                        return

                    number_stats = defaultdict(int)
                    for selection in number_selections:
                        number_stats[selection.number_choice.number] += 1

                    sorted_stats = sorted(number_stats.items(), key=lambda x: x[1], reverse=True)
                    response = "<b>Статистика чисел за все время:</b>\n\n"

                    for number, count in sorted_stats:
                        interpretation = session.query(NumberChoice).filter_by(number=number).first()
                        if interpretation:
                            response += f"<b>{number}</b>: {count} раз(а) - {interpretation.interpretation}\n\n"

                response = response.strip()
                send_long_message(bot, call.message.chat.id, response, parse_mode='HTML')
                logger.info(f"Отправлена полная статистика {stat_type} для пользователя {user.id}")
        except Exception as e:
            logger.error(f"Ошибка в handle_all_stat_selection: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при получении статистики.")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("list_"))
    def handle_list_selection(call):
        try:
            list_type = call.data.replace("list_", "")
            logger.info(f"Запрошен список трактовок типа {list_type}, пользователь: {call.from_user.id}")

            with SessionLocal() as session:
                if list_type == "time":
                    time_choices = session.query(TimeChoice).all()
                    response = "<b>Трактовки времени:</b>\n\n"
                    interpretations = {}

                    for choice in time_choices:
                        if choice.time_range.time_range not in interpretations:
                            interpretations[choice.time_range.time_range] = {}
                        interpretations[choice.time_range.time_range][choice.choice] = choice.interpretation

                    for period, choices in interpretations.items():
                        response += f"<b>{period}</b>\n"
                        for time, interpretation in choices.items():
                            safe_time = time.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                            safe_interpretation = interpretation.replace('&', '&amp;').replace('<', '&lt;').replace('>',
                                                                                                                    '&gt;')
                            response += f"<b>{safe_time}</b>: {safe_interpretation}\n"
                        response += "\n"

                elif list_type == "numbers":
                    number_choices = session.query(NumberChoice).all()
                    response = "<b>Трактовки чисел:</b>\n\n"

                    for choice in number_choices:
                        safe_number = str(choice.number).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                        safe_interpretation = choice.interpretation.replace('&', '&amp;').replace('<', '&lt;').replace(
                            '>', '&gt;')
                        response += f"<b>{safe_number}</b>: {safe_interpretation}\n\n"

                response = response.strip()
                send_long_message(bot, call.message.chat.id, response, parse_mode='HTML')
                logger.info(f"Отправлен список трактовок {list_type}")
        except Exception as e:
            logger.error(f"Ошибка в handle_list_selection: {e}", exc_info=True)
            bot.send_message(call.message.chat.id, "Произошла ошибка при получении списка трактовок.")
