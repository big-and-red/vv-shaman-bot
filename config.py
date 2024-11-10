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
    SQLALCHEMY_DATABASE_URI = (f'postgresql+{PG_DRIVER}://'
                               f'{POSTGRESQL_USER}:'
                               f'{POSTGRESQL_PASSWORD}@'
                               f'{POSTGRESQL_HOST}:'
                               f'{POSTGRESQL_PORT}/'
                               f'{POSTGRESQL_DBNAME}')
