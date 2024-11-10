import calendar
from typing import List, Tuple, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton  # Импорты для telebot


class TelegramCalendar:
    def __init__(self, locale: str = "en"):
        """
        Инициализация календаря с возможностью выбора языка.

        :param locale: Язык календаря (по умолчанию английский)
        """
        self.locale = locale

    def create_calendar(self, year: int, month: int) -> InlineKeyboardMarkup:
        """
        Создаёт инлайн-календарь для указанного года и месяца.

        :param year: Год для календаря
        :param month: Месяц для календаря
        :return: InlineKeyboardMarkup с кнопками
        """
        cal = calendar.monthcalendar(year, month)
        keyboard = InlineKeyboardMarkup(row_width=7)

        # Заголовок с месяцем и годом
        keyboard.add(InlineKeyboardButton(f'{calendar.month_name[month]} {year}', callback_data='ignore'))

        # Дни недели (вы можете перевести на нужный язык)
        days_of_week: List[str] = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        keyboard.add(*[InlineKeyboardButton(day, callback_data='ignore') for day in days_of_week])

        # Заполнение дней месяца
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(" ", callback_data="ignore"))  # Пустая клетка
                else:
                    row.append(InlineKeyboardButton(str(day), callback_data=f"day_{day}"))
            keyboard.add(*row)

        # Добавляем кнопки для перехода на следующий/предыдущий месяц
        keyboard.add(
            InlineKeyboardButton('<', callback_data=f"prev_{year}_{month}"),
            InlineKeyboardButton('>', callback_data=f"next_{year}_{month}")
        )

        return keyboard

    def handle_callback(self, callback_data: str, current_year: int, current_month: int) -> Tuple[
        Optional[int], Optional[int], Optional[int]]:
        """
        Обрабатывает нажатие на кнопку и возвращает год, месяц, день.

        :param callback_data: Данные, полученные при нажатии кнопки
        :param current_year: Текущий выбранный год
        :param current_month: Текущий выбранный месяц
        :return: Кортеж (год, месяц, день) или (None, None, None) для команд без даты
        """
        if callback_data.startswith("day_"):
            day = int(callback_data.split("_")[1])
            return current_year, current_month, day  # Возвращаем текущий год и месяц
        elif callback_data.startswith("prev_") or callback_data.startswith("next_"):
            year, month = map(int, callback_data.split("_")[1:])
            if "prev_" in callback_data:
                month -= 1
                if month == 0:
                    month = 12
                    year -= 1
            elif "next_" in callback_data:
                month += 1
                if month == 13:
                    month = 1
                    year += 1
            return year, month, None  # Возвращаем новый год и месяц
        return None, None, None

    def process_callback(self, callback_data: str, current_year: int, current_month: int) -> InlineKeyboardMarkup:
        """
        Обрабатывает коллбэки для кнопок перехода между месяцами и выбора дня.

        :param callback_data: Данные кнопки
        :param current_year: Текущий выбранный год
        :param current_month: Текущий выбранный месяц
        :return: InlineKeyboardMarkup обновленного календаря
        """
        year, month, day = self.handle_callback(callback_data, current_year, current_month)
        if day is not None:
            # Здесь можно обработать выбор дня, например, отправить сообщение с выбранной датой
            return None
        else:
            # Переход на другой месяц
            if year is not None and month is not None:
                return self.create_calendar(year, month)
            return self.create_calendar(current_year, current_month)
