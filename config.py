import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
MINI_APP_URL = os.getenv("MINI_APP_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")