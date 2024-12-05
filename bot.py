import telebot
from telebot import apihelper

from config import Config
from handlers.command_handlers import register_command_handlers
from handlers.callback_handlers import register_callback_handlers
import logging
import time
import sys
from telebot.handler_backends import State, StatesGroup

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_log.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

apihelper.ENABLE_MIDDLEWARE = True


def run_bot():
    bot = telebot.TeleBot(Config.BOT_TOKEN)

    # Регистрируем обработчики команд и колбеков
    register_command_handlers(bot)
    register_callback_handlers(bot)

    # Обработчик всех ошибок
    @bot.middleware_handler(update_types=['message', 'callback_query'])
    def error_handler(bot_instance, update):
        try:
            return True
        except Exception as e:
            logger.error(f"Middleware error: {e}", exc_info=True)
            return True

    while True:
        try:
            logger.info("Bot started")
            bot.polling(none_stop=True, interval=1, timeout=60)
        except telebot.apihelper.ApiException as e:
            logger.error(f"API Exception: {e}", exc_info=True)
            time.sleep(15)
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            time.sleep(15)
        finally:
            logger.info("Bot stopped, attempting restart...")
            time.sleep(5)


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped manually")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical error occurred: {e}", exc_info=True)
        sys.exit(1)
