import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")  # userbot ka session

# Admin users (jo bot ko control kar sakte hain)
SUDO_USERS = [int(x) for x in os.getenv("SUDO_USERS", "").split(",") if x]
