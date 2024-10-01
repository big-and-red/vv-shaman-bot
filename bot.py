import telebot
from config import Config
from handlers.command_handlers import register_command_handlers
from handlers.callback_handlers import register_callback_handlers

bot = telebot.TeleBot(Config.BOT_TOKEN)

# Регистрируем обработчики команд и колбеков
register_command_handlers(bot)
register_callback_handlers(bot)

# Запуск бота
if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error occurred: {e}")
