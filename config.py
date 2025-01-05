import logging
import os
from dotenv import load_dotenv


class Config:
    load_dotenv()

    # TG
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # DB
    POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST')
    POSTGRESQL_PORT = os.getenv('POSTGRESQL_PORT')
    POSTGRESQL_USER = os.getenv('POSTGRESQL_USER')
    POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD')
    POSTGRESQL_DBNAME = os.getenv('POSTGRESQL_DBNAME')
    PG_SCHEMA = os.getenv('PG_SCHEMA')
    PG_DRIVER = os.getenv('PG_DRIVER')
    # SQLALCHEMY_DATABASE_URI = (f'postgresql+{PG_DRIVER}://'
    #                            f'{POSTGRESQL_USER}:'
    #                            f'{POSTGRESQL_PASSWORD}@'
    #                            f'{POSTGRESQL_HOST}:'
    #                            f'{POSTGRESQL_PORT}/'
    #                            f'{POSTGRESQL_DBNAME}')

    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'

    @classmethod
    def init_logger(cls, log_level=logging.INFO):
        """Инициализация логгера с уровнем логирования и базовой конфигурацией."""

        # Базовая конфигурация логирования
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Логгер вашего приложения
        logger = logging.getLogger("VVS-Logger")
        logger.info("Logger initialized with level: %s", logging.getLevelName(log_level))

        # Настройка логгера для SQLAlchemy
        # Оставляем только SQL-запросы (без параметров и другой информации)
        sql_logger = logging.getLogger('sqlalchemy.engine')
        sql_logger.setLevel(logging.INFO)  # Логи SQL-запросов

        # Отключаем вывод параметров запросов
        sql_engine_logger = logging.getLogger('sqlalchemy.engine.Engine')
        sql_engine_logger.setLevel(logging.INFO)

        # Отключаем логи о пулах соединений
        logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

        # Отключаем логи для диалектов (например, PostgreSQL)
        logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)

        return logger


class DevConfig(Config):
    logger = Config.init_logger()


def get_config_class():
    env = os.getenv('CONF_ENV', 'development')
    if env == 'production':
        pass
    elif env == 'testing':
        pass
    else:
        return DevConfig


current_config = get_config_class()
config_instance = current_config()
