import os
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

# Group chat ID for sending polls
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

