# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Discord 配置
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_IDS = [int(id) for id in os.getenv('GUILD_IDS', '').split(',') if id]

# Groq API 配置
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')

# Google Calendar 配置
GOOGLE_CREDENTIALS_PATH = os.getenv('GOOGLE_CREDENTIALS_PATH')
CALENDAR_ID = os.getenv('CALENDAR_ID', 'primary')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Taipei')