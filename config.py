import os
from dotenv import load_dotenv


class Config:
    load_dotenv()

    BOT_TOKEN = os.getenv('BOT_TOKEN')
