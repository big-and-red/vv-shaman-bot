import telebot
from telebot import types


def send_long_message(bot: telebot.TeleBot, chat_id: int, text: str, parse_mode=None):
    max_length = 4096

    # Если парсинг HTML не включен или сообщение короткое, просто отправляем
    if parse_mode != 'HTML' or len(text) <= max_length:
        for i in range(0, len(text), max_length):
            bot.send_message(chat_id, text[i:i + max_length], parse_mode=parse_mode)
        return

    # Разбиваем текст с учетом HTML-тегов
    parts = []
    current_part = ""
    open_tags = []  # Стек для отслеживания открытых тегов

    i = 0
    while i < len(text):
        # Проверяем, не встретили ли открывающий тег
        if text[i:i + 1] == '<' and i + 1 < len(text) and text[i + 1:i + 2] != '/':
            tag_end = text.find('>', i)
            if tag_end != -1:
                tag_content = text[i + 1:tag_end]
                tag_name = tag_content.split()[0]
                if tag_name in ['b', 'i', 'u', 'a', 'code', 'pre', 'strong', 'em']:
                    open_tags.append(tag_name)

        # Проверяем, не встретили ли закрывающий тег
        elif text[i:i + 2] == '</' and i + 2 < len(text):
            tag_end = text.find('>', i)
            if tag_end != -1:
                tag_name = text[i + 2:tag_end]
                if open_tags and open_tags[-1] == tag_name:
                    open_tags.pop()

        current_part += text[i]
        i += 1

        # Если текущая часть достигла максимальной длины или мы близки к концу
        if len(current_part) >= max_length - 100 or i == len(text):
            # Закрываем все открытые теги
            for tag in reversed(open_tags):
                current_part += f"</{tag}>"

            parts.append(current_part)

            # Если это не последняя часть, начинаем новую
            if i < len(text):
                current_part = ""
                # Открываем снова все теги для новой части
                for tag in open_tags:
                    current_part += f"<{tag}>"

    # Отправляем все части
    for part in parts:
        bot.send_message(chat_id, part, parse_mode=parse_mode)


def generate_time_range_buttons(time_ranges):
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)  # Один столбец
    for time_range in time_ranges:
        button = telebot.types.InlineKeyboardButton(
            text=time_range.time_range,
            callback_data=f'range_{time_range.id}'  # добавляем id временного промежутка
        )
        markup.add(button)
    return markup


def generate_time_choice_buttons(time_choices):
    markup = telebot.types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        telebot.types.InlineKeyboardButton(choice.choice, callback_data=f"time_{choice.time_range_id}_{choice.id}")
        for choice in time_choices
    ]
    markup.add(*buttons)
    markup.add(telebot.types.InlineKeyboardButton("Назад", callback_data="back"))
    return markup
