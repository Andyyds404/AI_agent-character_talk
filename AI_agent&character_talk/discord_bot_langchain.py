# discord_bot_langchain.py - 簡化版本
import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import datetime as dt
from dotenv import load_dotenv
from calendar_service import CalendarService
from Langchain_Calendar import CalendarAssistant
from character_system import VirtualSandboxSociety, CharacterTrait, SceneSetting
from groq import Groq
import asyncio

load_dotenv()

class LangChainCalendarBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        
        # 初始化
        groq_key = os.getenv('GROQ_API_KEY')
        
        # LangChain 日曆助理
        self.calendar_assistant = CalendarAssistant(
            groq_api_key=groq_key,
            timezone=os.getenv('TIMEZONE', 'Asia/Taipei')
        )
        
        # Google Calendar 
        try:
            self.calendar_service = CalendarService(
                os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json'),
                os.getenv('TIMEZONE', 'Asia/Taipei')
            )
            print("✅ Google Calendar 服務初始化成功")
        except Exception as e:
            print(f"⚠️  Google Calendar 服務初始化失敗: {e}")
            self.calendar_service = None
        
        self.calendar_id = os.getenv('CALENDAR_ID', 'primary')
        self.virtual_society = VirtualSandboxSociety(Groq(api_key=groq_key))
        self.current_mode = "normal"
        self.current_role = None
        self.active_conversations = {}
        self.user_states = {}
    
    async def on_ready(self):
        """當機器人準備好時"""
        print(f'✅ {self.user} 已成功登入！ (LangChain 版本)')
        print(f'🤖 LangChain 系統已初始化')
        await self.change_presence(activity=discord.Game(name="LangChain 助理 | !help"))

# 創建bot
bot = LangChainCalendarBot()