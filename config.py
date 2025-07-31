import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
