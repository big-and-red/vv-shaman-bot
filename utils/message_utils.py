import telebot
from telebot import types


def send_long_message(bot: telebot.TeleBot, chat_id: int, text: str, parse_mode=None):
    max_length = 4096
    for i in range(0, len(text), max_length):
        bot.send_message(chat_id, text[i:i + max_length], parse_mode=parse_mode)


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
