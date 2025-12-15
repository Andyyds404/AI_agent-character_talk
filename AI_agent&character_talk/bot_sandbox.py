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
from discord_bot_langchain import bot

load_dotenv()

# ============================
# 虛擬沙盒命令
# ============================

@bot.command(name="sandbox")
async def sandbox_command(ctx):
    """啟動虛擬沙盒社會"""
    
    class RoleButton(Button):
        def __init__(self, role_key, character):
            super().__init__(
                label=character.name[:15],
                style=discord.ButtonStyle.primary,
                emoji="🎭"
            )
            self.role_key = role_key
            self.character = character
        
        async def callback(self, interaction):
            user_id = interaction.user.id
            
            # 開始新對話
            bot.active_conversations[user_id] = {
                "role_key": self.role_key,
                "character": self.character,
                "history": [],
                "current_scene": bot.virtual_society.current_scene
            }
            
            bot.current_mode = "sandbox"
            bot.current_role = self.role_key
            
            embed = discord.Embed(
                title=f"🎭 與 {self.character.name} 對話開始",
                description=f"**{self.character.profession}**\n\n性格: {self.character.personality}",
                color=discord.Color.purple()
            )
            
            embed.add_field(
                name="💬 使用方式",
                value="直接輸入訊息與角色對話\n輸入 `!stop` 結束對話",
                inline=False
            )
            
            embed.add_field(
                name="📍 當前場景",
                value=f"{bot.virtual_society.current_scene.location}\n氛圍: {bot.virtual_society.current_scene.atmosphere}",
                inline=True
            )
            
            await interaction.response.edit_message(
                content=f"🎮 虛擬沙盒社會",
                embed=embed,
                view=None
            )
    
    # 獲取所有角色
    all_characters = bot.virtual_society.get_all_characters()
    
    if not all_characters:
        embed = discord.Embed(
            title="🎮 虛擬沙盒社會",
            description="還沒有任何角色，請先創建角色",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # 創建分類選擇
    embed = discord.Embed(
        title="🎮 虛擬沙盒社會",
        description="選擇角色分類開始對話：",
        color=discord.Color.purple()
    )
    
    view = View()
    
    # 預設角色按鈕
    default_chars = {k: v for k, v in all_characters.items() if not k.startswith('custom_')}
    if default_chars:
        default_button = Button(
            label="📦 預設角色",
            style=discord.ButtonStyle.primary,
            emoji="📦",
            custom_id="default_chars"
        )
        view.add_item(default_button)
    
    # 自定義角色按鈕
    custom_chars = {k: v for k, v in all_characters.items() if k.startswith('custom_')}
    if custom_chars:
        custom_button = Button(
            label="🎨 自定義角色",
            style=discord.ButtonStyle.success,
            emoji="🎨",
            custom_id="custom_chars"
        )
        view.add_item(custom_button)
    
    await ctx.send(embed=embed, view=view)
    
    # 處理按鈕點擊
    @bot.event
    async def on_interaction(interaction):
        if interaction.data.get('custom_id') == 'default_chars':
            await show_role_selection(interaction, default_chars, "📦 預設角色")
        elif interaction.data.get('custom_id') == 'custom_chars':
            await show_role_selection(interaction, custom_chars, "🎨 自定義角色")
    
    async def show_role_selection(interaction, characters_dict, category_name):
        """顯示角色選擇"""
        embed = discord.Embed(
            title=f"🎭 {category_name}",
            description="請選擇一個角色：",
            color=discord.Color.blue()
        )
        
        view = View()
        
        # 添加角色按鈕
        for role_key, character in list(characters_dict.items())[:12]:  # 限制最多12個
            button = RoleButton(role_key, character)
            view.add_item(button)
        
        await interaction.response.edit_message(embed=embed, view=view)

@bot.command(name="scene")
async def scene_command(ctx, action: str = None, scene_name: str = None):
    """場景管理命令"""
    
    user_id = ctx.author.id
    
    if user_id not in bot.active_conversations:
        embed = discord.Embed(
            title="⚠️  場景管理",
            description="請先使用 `!sandbox` 選擇角色開始對話",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    conversation = bot.active_conversations[user_id]
    character = conversation["character"]
    
    if action == "list":
        # 列出可用場景
        scenes = bot.virtual_society.get_all_scenes()
        
        embed = discord.Embed(
            title="🎭 可用場景列表",
            description="請選擇一個場景切換：",
            color=discord.Color.blue()
        )
        
        for key, location in scenes.items():
            scene_info = bot.virtual_society._merge_scenes()
            embed.add_field(
                name=f"🔹 {key}",
                # value=f"**{location.location}**",
                value=f"**{location.location}**\n氛圍: {location.atmosphere}\n時間: {location.time_period}",
                inline=True
            )
        
        embed.set_footer(text="使用 !scene change [場景名稱] 切換場景")
        await ctx.send(embed=embed)
        
    elif action == "change" and scene_name:
        # 切換場景
        result = bot.virtual_society.setup_scene(scene_name)
        
        if result.startswith("✅"):
            # 更新對話中的場景
            new_scene = bot.virtual_society.get_current_scene_info()
            conversation["current_scene"] = new_scene
            
            embed = discord.Embed(
                title="🎬 場景切換成功，切換至"+new_scene["location"],
                description=result,
                color=discord.Color.green()
            )
            
            # 記錄場景變更
            conversation.get("history", []).append({
                "role": "system",
                "content": f"場景切換到 {new_scene["location"]}",
                "timestamp": dt.datetime.now().isoformat()
            })
        else:
            embed = discord.Embed(
                title="❌ 場景切換失敗",
                description=result,
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
        
    elif action == "info":
        # 顯示當前場景資訊
        scene_info = bot.virtual_society.get_current_scene_info()
        
        embed = discord.Embed(
            title="🎭 當前場景資訊",
            color=discord.Color.purple()
        )
        
        embed.add_field(name="📍 地點", value=scene_info["location"], inline=True)
        embed.add_field(name="⏰ 時間", value=scene_info["time_period"], inline=True)
        embed.add_field(name="🌫️ 氛圍", value=scene_info["atmosphere"], inline=True)
        
        await ctx.send(embed=embed)
        
    else:
        # 顯示幫助
        embed = discord.Embed(
            title="🎭 場景管理命令",
            description="管理虛擬沙盒的場景設定",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="可用命令",
            value="""
            **!scene list** - 列出所有可用場景
            **!scene change [名稱]** - 切換到指定場景
            **!scene info** - 顯示當前場景資訊
            """,
            inline=False
        )
        
        # 列出可用場景
        scenes = bot.virtual_society.get_all_scenes()
        value = ""
        for key, location in scenes.items():
            scene_info = bot.virtual_society._merge_scenes()
            value += f"🔹 {key}"
        embed.add_field(
            name="可用場景",
            value=value,
            inline=False
        )
        
        await ctx.send(embed=embed)

@bot.command(name="stop")
async def stop_command(ctx):
    """停止當前對話"""
    user_id = ctx.author.id
    
    if user_id in bot.active_conversations:
        role_name = bot.active_conversations[user_id]["character"].profession
        del bot.active_conversations[user_id]
        await ctx.send(f"✅ 已結束與 {role_name} 的對話")
    else:
        await ctx.send("⚠️  沒有正在進行的對話")

@bot.command(name="mode")
async def mode_command(ctx):
    """顯示當前模式"""
    embed = discord.Embed(
        title="🎮 系統模式狀態",
        color=discord.Color.blue()
    )
    
    if bot.current_mode == "sandbox" and bot.current_role:
        character = bot.virtual_society.characters.get(bot.current_role)
        if character:
            embed.description = f"🎭 LangChain 角色模擬模式\n角色: {character.profession}"
        else:
            embed.description = "🎭 LangChain 角色模擬模式"
    else:
        embed.description = "📱 LangChain 正常模式"
    
    await ctx.send(embed=embed)

# ============================
# 訊息處理
# ============================

@bot.event
async def on_message(message):
    """處理訊息"""
    
    if message.author == bot.user:
        return
    
    user_id = message.author.id
    
    # 檢查是否在沙盒對話中
    if user_id in bot.active_conversations:
        # 檢查停止指令
        if message.content.lower() in ["停止", "結束", "exit", "stop", "quit", "goodbye","離開"]:
            del bot.active_conversations[user_id]
            await message.channel.send("✅ 對話已結束，返回一般模式")
            return
        
        # 如果不是指令，視為對話
        if not message.content.startswith("!"):
            conversation = bot.active_conversations[user_id]
            character = conversation["character"]
            
            try:
                # 使用增強的角色回應生成
                response = bot.virtual_society.generate_role_response(
                    conversation["role_key"], 
                    message.content
                )
                
                # 更新對話歷史（包含背景發展）
                bot.virtual_society.update_conversation_with_background(
                    conversation["role_key"],
                    message.content,
                    response
                )
                
                await message.channel.send(f"**{character.name}** ({character.profession}): {response}")
            except Exception as e:
                await message.channel.send(f"❌ 對話錯誤: {str(e)}")
            
            return
    
    # 處理指令
    await bot.process_commands(message)

# ============================
# 客製化功能命令
# ============================

@bot.command(name="create")
async def create_command(ctx, item_type: str = None):
    """創建自定義內容
    
用法:
!create character - 創建自定義角色
!create scene - 創建自定義場景
!create event - 創建自定義事件
!create background - 創建自定義背景故事
    """
    
    if item_type == "character":
        embed = discord.Embed(
            title="🎭 創建自定義角色",
            description="請按照以下格式提供角色資訊：",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📝 格式",
            value="""
            ```
名稱: [角色名稱]
年齡: [年齡]
性別: [性別]
職業: [職業]
格: [性格特徵]
價值觀: [價值觀1, 價值觀2, ...]
說話風格: [說話風格]
背景故事: [背景故事]
興趣: [興趣1, 興趣2, ...]
            ```""",
            inline=False
        )
        
        embed.add_field(
            name="📋 範例",
            value="""
            ```
名稱: 張老師
年齡: 35
性別: 男
職業: 數學教師
性格: 耐心、嚴謹、幽默
價值觀: 教育、誠實、成長
說話風格: 清晰、有條理、親切
背景故事: 有10年教學經驗的數學老師，熱愛AI推廣
興趣: 數學、閱讀、登山、生成式AI
            ```""",
            inline=False
        )
        
        embed.set_footer(text="請複製格式並填寫後發送，我會為您創建角色")
        
        await ctx.send(embed=embed)
        
        # 等待用戶輸入
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=120.0, check=check)
            await process_character_creation(ctx, msg.content)
        except asyncio.TimeoutError:
            await ctx.send("操作逾時，請重新 !create character")
            
    elif item_type == "scene":
        embed = discord.Embed(
            title="🏢 創建自定義場景",
            description="請按照以下格式提供場景資訊：",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📝 格式",
            value="""
            ```
名稱: [場景名稱]
地點: [地點]
氛圍: [氛圍]
時間: [時間段]
描述: [詳細描述]
天氣: [天氣]
物件: [物件1, 物件2, ...]
聲音: [聲音1, 聲音2, ...]
            ```""",
            inline=False
        )
        
        embed.add_field(
            name="📋 範例",
            value="""
            ```
名稱: 海邊咖啡廳
地點: 海濱咖啡廳
氛圍: 浪漫、放鬆
時間: 黃昏
描述: 位於海邊的咖啡廳，可以聽到海浪聲
天氣: 晴朗
物件: 咖啡桌, 沙發, 書籍, 畫作
聲音: 海浪聲, 輕音樂, 咖啡機聲
            ```""",
            inline=False
        )
        
        embed.set_footer(text="請複製格式並填寫後發送")
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=120.0, check=check)
            await process_scene_creation(ctx, msg.content)
        except asyncio.TimeoutError:
            await ctx.send("操作逾時")
            
    elif item_type == "background":
        embed = discord.Embed(
            title="📖 自定義背景故事",
            description="請按照以下格式提供背景故事：",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="📝 格式",
            value="""
            ```
標題: [背景標題]
內容: [背景故事內容]
角色: [相關角色名稱，可選]
            ```""",
            inline=False
        )
        
        embed.add_field(
            name="📋 範例",
            value="""
            ```
標題: 王總監的過去
內容: 王總監年輕時曾在國外留學，主修商業管理。回國後從基層做起，憑藉出色的能力和努力，在10年內晉升為公司總監。他有一個幸福的家庭，但在事業上仍有更高的追求。
角色: 王總監
            ```""",
            inline=False
        )
        
        embed.set_footer(text="請複製格式並填寫後發送")
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=120.0, check=check)
            await process_background_creation(ctx, msg.content)
        except asyncio.TimeoutError:
            await ctx.send("操作逾時")
            
    else:
        embed = discord.Embed(
            title="🎨 自定義內容創建",
            description="建立個人化角色模擬情境",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="可用命令",
            value="""
            **!create character** - 創建自定義角色
            **!create scene** - 創建自定義場景
            **!create background** - 創建自定義背景故事
            """,
            inline=False
        )
        
        embed.add_field(
            name="💡 提示",
            value="請按照說明格式填寫資訊",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def process_character_creation(ctx, content: str):
    """處理角色創建"""
    try:
        data = {}
        lines = content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in ['價值觀', '興趣']:
                    data[key] = [v.strip() for v in value.split(',')]
                elif key == '年齡':
                    data[key] = int(value)
                else:
                    data[key] = value
        
        # 創建角色
        character = bot.virtual_society.create_custom_character(
            name=data.get('名稱', '未命名'),
            age=data.get('年齡', 25),
            gender=data.get('性別', '未指定'),
            profession=data.get('職業', '未指定'),
            personality=data.get('性格', '中性'),
            values=data.get('價值觀', []),
            speech_style=data.get('說話風格', '普通'),
            background=data.get('背景故事', '無'),
            interests=data.get('興趣', [])
        )
        
        if character:
            embed = discord.Embed(
                title="✅ 角色創建成功",
                description=f"已成功創建角色: **{character.name}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="👤 名稱", value=character.name, inline=True)
            embed.add_field(name="🎭 職業", value=character.profession, inline=True)
            embed.add_field(name="✨ 性格", value=character.personality, inline=True)
            
            embed.add_field(
                name="💬 使用方式",
                value=f"使用 `!sandbox` 選擇角色，在自定義分類中尋找",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 角色創建失敗，請檢查格式是否正確")
            
    except Exception as e:
        await ctx.send(f"❌{str(e)}")

async def process_scene_creation(ctx, content: str):
    """處理場景創建"""
    try:
        data = {}
        lines = content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if key in ['物件', '聲音']:
                    data[key] = [v.strip() for v in value.split(',')]
                else:
                    data[key] = value
        
        scene = bot.virtual_society.create_custom_scene(
            name=data.get('名稱', '未命名場景'),
            location=data.get('地點', '未知地點'),
            atmosphere=data.get('氛圍', '中性'),
            time_period=data.get('時間', '現在'),
            description=data.get('描述', ''),
            weather=data.get('天氣', '晴朗'),
            objects=data.get('物件', []),
            background_sounds=data.get('聲音', [])
        )
        
        if scene:
            embed = discord.Embed(
                title="✅ 場景創建成功",
                description=f"已成功創建場景: **{scene.name}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="📍 地點", value=scene.location, inline=True)
            embed.add_field(name="⏰ 時間", value=scene.time_period, inline=True)
            embed.add_field(name="🌫️ 氛圍", value=scene.atmosphere, inline=True)
            
            if scene.description:
                embed.add_field(name="📝 描述", value=scene.description, inline=False)
            
            embed.add_field(
                name="切換方式",
                value=f"使用 `!scene change {scene.name}` 切換到此場景",
                inline=False
            )
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 場景創建失敗，請檢查格式是否正確")
            
    except Exception as e:
        await ctx.send(f"❌ 處理失敗: {str(e)}")

async def process_background_creation(ctx, content: str):
    """處理背景故事創建"""
    try:
        data = {}
        lines = content.split('\n')
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                data[key] = value
        
        background = bot.virtual_society.create_custom_background(
            title=data.get('標題', '未命名背景'),
            content=data.get('內容', ''),
            character_name=data.get('角色', '')
        )
        
        if background:
            embed = discord.Embed(
                title="✅ 背景故事建立成功",
                description=f"已成功創建背景故事: **{background['title']}**",
                color=discord.Color.green()
            )
            
            embed.add_field(name="📖 標題", value=background['title'], inline=True)
            
            if background.get('character_name'):
                embed.add_field(name="👤 相關角色", value=background['character_name'], inline=True)
            
            if background.get('content'):
                embed.add_field(name="📝 內容", value=background['content'][:150] + "...", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("❌ 背景故事創建失敗")
            
    except Exception as e:
        await ctx.send(f"❌ 處理失敗: {str(e)}")

@bot.command(name="list")
async def list_command(ctx, item_type: str = None):
    """列出自定義內容
    
用法:
!list characters - 列出所有角色（包含自定義）
!list scenes - 列出所有場景（包含自定義）
!list backgrounds - 列出所有背景故事
    """
    
    if item_type == "characters":
        characters = bot.virtual_society.get_all_characters()
        
        if not characters:
            await ctx.send("📭 還沒有任何角色")
            return
        
        embed = discord.Embed(
            title="🎭 所有角色列表",
            description=f"共 {len(characters)} 個角色",
            color=discord.Color.blue()
        )
        
        # 分組顯示
        default_chars = []
        custom_chars = []
        
        for key, char in characters.items():
            if key.startswith('custom_'):
                custom_chars.append(char)
            else:
                default_chars.append(char)
        
        if default_chars:
            default_text = "\n".join([f"• **{char.name}** ({char.profession})" for char in default_chars[:5]])
            embed.add_field(name="📦 預設角色", value=default_text, inline=False)
        
        if custom_chars:
            custom_text = "\n".join([f"• **{char.name}** ({char.profession})" for char in custom_chars[:5]])
            embed.add_field(name="🎨 自定義角色", value=custom_text, inline=False)
            
            if len(custom_chars) > 5:
                embed.set_footer(text=f"還有 {len(custom_chars)-5} 個自定義角色未顯示")
        
        await ctx.send(embed=embed)
        
    elif item_type == "scenes":
        scenes = bot.virtual_society.get_all_scenes()
        
        if not scenes:
            await ctx.send("📭 還沒有任何場景")
            return
        
        embed = discord.Embed(
            title="🏢 所有場景列表",
            description=f"共 {len(scenes)} 個場景",
            color=discord.Color.green()
        )
        
        default_scenes = []
        custom_scenes = []
        
        for name, scene in scenes.items():
            if name in ["辦公室", "咖啡廳", "公園", "虛擬對話空間"]:
                default_scenes.append(scene)
            else:
                custom_scenes.append(scene)
        
        if default_scenes:
            default_text = "\n".join([f"• **{scene.name}** - {scene.location}" for scene in default_scenes])
            embed.add_field(name="📦 預設場景", value=default_text, inline=False)
        
        if custom_scenes:
            custom_text = "\n".join([f"• **{scene.name}** - {scene.location}" for scene in custom_scenes[:5]])
            embed.add_field(name="🎨 自定義場景", value=custom_text, inline=False)
            
            if len(custom_scenes) > 5:
                embed.set_footer(text=f"還有 {len(custom_scenes)-5} 個自定義場景未顯示")
        
        await ctx.send(embed=embed)
        
    elif item_type == "backgrounds":
        backgrounds = bot.virtual_society.get_all_backgrounds()
        
        if not backgrounds:
            await ctx.send("📭 還沒有任何背景故事")
            return
        
        embed = discord.Embed(
            title="📖 所有背景故事列表",
            description=f"共 {len(backgrounds)} 個背景故事",
            color=discord.Color.gold()
        )
        
        for bg_id, bg in list(backgrounds.items())[:5]:
            title = bg.get('title', '未命名')
            character = bg.get('character_name', '未指定角色')
            
            embed.add_field(
                name=f"📚 {title}",
                value=f"角色: {character}\n內容: {bg.get('content', '')[:80]}...",
                inline=False
            )
        
        if len(backgrounds) > 5:
            embed.set_footer(text=f"還有 {len(backgrounds)-5} 個背景故事未顯示")
        
        await ctx.send(embed=embed)
        
    else:
        embed = discord.Embed(
            title="📋 內容列表",
            description="查看您創建的虛擬沙盒內容",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="可用命令",
            value="""
            **!list characters** - 列出所有角色
            **!list scenes** - 列出所有場景
            **!list backgrounds** - 列出所有背景故事
            """,
            inline=False
        )
        
        embed.add_field(
            name="💡 提示",
            value="這些列表包含您創建的自定義內容和預設內容",
            inline=False
        )
        
        await ctx.send(embed=embed)

@bot.command(name="delete")
async def delete_command(ctx, item_type: str = None, item_name: str = None):
    """刪除自定義內容
    
    用法:
    !delete character [角色名稱] - 刪除自定義角色
    !delete scene [場景名稱] - 刪除自定義場景
    """
    
    if not item_type or not item_name:
        embed = discord.Embed(
            title="🗑️ 刪除",
            description="刪除您創建的模擬內容",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="可用命令",
            value="""
            **!delete character [角色名稱]** - 刪除自定義角色
            **!delete scene [場景名稱]** - 刪除自定義場景
            
            刪除後無法恢復！
            """,
            inline=False
        )
        
        await ctx.send(embed=embed)
        return
    
    if item_type == "character":
        embed = discord.Embed(
            title="確認刪除角色",
            description=f"您確定要刪除角色 **{item_name}** 嗎？",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="警告",
            value="刪除後角色將永久消失，無法恢復！",
            inline=False
        )
        
        embed.set_footer(text="輸入 '確認刪除' 繼續，輸入其他內容取消")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            
            if msg.content == "確認刪除":
                success = bot.virtual_society.delete_custom_character(item_name)
                
                if success:
                    await ctx.send(f"✅ 已成功刪除角色: {item_name}")
                else:
                    await ctx.send(f"❌ 刪除失敗，角色 '{item_name}' 不存在或不是自定義角色")
            else:
                await ctx.send("❌ 刪除已取消")
                
        except asyncio.TimeoutError:
            await ctx.send("操作逾時")
    
    elif item_type == "scene":
        # 確認刪除
        embed = discord.Embed(
            title="⚠️ 確認刪除場景",
            description=f"您確定要刪除場景 **{item_name}** 嗎？",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="警告",
            value="刪除後場景將永久消失，無法恢復！",
            inline=False
        )
        
        embed.set_footer(text="輸入 '確認刪除' 繼續，輸入其他內容取消")
        
        await ctx.send(embed=embed)
        
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            
            if msg.content == "確認刪除":
                success = bot.virtual_society.delete_custom_scene(item_name)
                
                if success:
                    await ctx.send(f"✅ 已成功刪除場景: {item_name}")
                else:
                    await ctx.send(f"❌ 刪除失敗，場景 '{item_name}' 不存在或不是自定義場景")
            else:
                await ctx.send("❌ 刪除已取消")
                
        except asyncio.TimeoutError:
            await ctx.send("操作逾時")
    
    else:
        await ctx.send("❌ 不支援的刪除類型")

@bot.command(name="custom")
async def custom_dashboard(ctx):
    """自定義儀表板"""
    
    embed = discord.Embed(
        title="🎨 自定義儀表板",
        description="管理自定義內容",
        color=discord.Color.blue()
    )
    
    # 獲取統計數據
    characters = bot.virtual_society.get_all_characters()
    scenes = bot.virtual_society.get_all_scenes()
    backgrounds = bot.virtual_society.get_all_backgrounds()
    
    # 計算自定義數量
    custom_char_count = len([c for c in characters.values() if c.name.startswith('custom_')])
    custom_scene_count = len([s for s in scenes.values() if s.name not in ["辦公室", "咖啡廳", "公園", "虛擬對話空間"]])
    
    embed.add_field(
        name="📊 內容統計",
        value=f"""
        • **角色**: {len(characters)} 個 ({custom_char_count} 個自定義)
        • **場景**: {len(scenes)} 個 ({custom_scene_count} 個自定義)
        • **背景故事**: {len(backgrounds)} 個
        """,
        inline=False
    )
    
    embed.add_field(
        name="🎯 創建命令",
        value="""
        **!create character** - 創建角色
        **!create scene** - 創建場景
        **!create background** - 創建背景故事
        """,
        inline=True
    )
    
    embed.add_field(
        name="📋 查看命令",
        value="""
        **!list characters** - 查看角色
        **!list scenes** - 查看場景\
        **!list backgrounds** - 查看背景
        """,
        inline=True
    )
    
    embed.add_field(
        name="🗑️ 管理命令",
        value="""
        **!delete character** - 刪除角色
        **!delete scene** - 刪除場景
        """,
        inline=False
    )
    
    embed.add_field(
        name="💡 使用提示",
        value="""
1. 創建時請仔細按照格式填寫
2. 所有內容都會自動保存
3. 可以隨時查看和刪除
4. 重啟機器人後內容仍然存在
        """,
        inline=False
    )    
    await ctx.send(embed=embed)

@bot.command(name="bind")
async def bind_command(ctx, action: str = None, target_name: str = None, target_type: str = None):
    """連結背景故事和事件到角色
    
    用法:
    !bind list - 列出已連結的角色
    !bind background [角色名稱] [背景ID] - 連結背景故事
    !bind info [角色名稱] - 查看角色資訊
    """
    
    if action == "list":
        characters_with_bg = bot.virtual_society.get_character_with_backgrounds()
        
        if not characters_with_bg:
            embed = discord.Embed(
                title="📭 連結角色列表",
                description="還沒有任何角色被連結背景故事",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="📋 連結角色列表",
            description=f"共 {len(characters_with_bg)} 個角色有連結",
            color=discord.Color.blue()
        )
        
        for char_info in characters_with_bg:
            char = char_info["character"]
            embed.add_field(
                name=f"🎭 {char.name} ({char.profession})",
                value=f"背景故事: {char_info['background_count']}個\n使用: `!bind info {char.name}`",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    elif action == "background" and target_name:
        backgrounds = bot.virtual_society.get_all_backgrounds()
        
        if not backgrounds:
            await ctx.send("📭 還沒有創建任何背景故事，請先使用 `!create background` 創建")
            return
        
        all_characters = bot.virtual_society.get_all_characters()
        character_exists = False
        for char in all_characters.values():
            if char.name == target_name:
                character_exists = True
                break
        
        if not character_exists:
            await ctx.send(f"❌ 角色 '{target_name}' 不存在")
            return
        
        embed = discord.Embed(
            title="📖 選擇背景故事",
            description=f"為角色 **{target_name}** 選擇要連結的背景故事：",
            color=discord.Color.purple()
        )
        
        for bg_id, bg in list(backgrounds.items())[:5]:
            title = bg.get('title', '未命名')
            content_preview = bg.get('content', '')[:80] + "..." if len(bg.get('content', '')) > 80 else bg.get('content', '')
            
            embed.add_field(
                name=f"📚 {title}",
                value=f"ID: `{bg_id}`\n內容: {content_preview}",
                inline=False
            )
        
        embed.set_footer(text="請輸入背景故事的 ID 進行連結")
        await ctx.send(embed=embed)
        
        # 等待用戶輸入背景ID
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            background_id = msg.content.strip()
            
            if background_id in backgrounds:
                story_id = bot.virtual_society.bind_background_to_character(
                    target_name, 
                    backgrounds[background_id]
                )
                
                embed = discord.Embed(
                    title="✅ 背景故事連結成功",
                    description=f"已將背景故事連結到角色 **{target_name}**",
                    color=discord.Color.green()
                )
                
                bg = backgrounds[background_id]
                embed.add_field(name="📖 背景標題", value=bg.get('title', '未命名'), inline=True)
                embed.add_field(name="🎭 連結角色", value=target_name, inline=True)
                embed.add_field(name="🔗 故事ID", value=story_id, inline=True)
                
                embed.set_footer(text="角色現在會記得這個背景故事")
                await ctx.send(embed=embed)
                bot.virtual_society.bind_background_to_character(target_name, backgrounds[background_id])
    
            else:
                await ctx.send("❌ 找不到指定的背景故事ID")
                
        except asyncio.TimeoutError:
            await ctx.send("操作逾時")
    
    elif action == "info" and target_name:
        # 查看角色連結資訊
        bg_info = bot.virtual_society.get_character_background_info(target_name)
        
        if not bg_info:
            embed = discord.Embed(
                title=f"📭 {target_name} 的連結資訊",
                description="該角色還沒有連結任何背景故事",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="💡 建議",
                value=f"使用 `!bind background {target_name}` 連結背景故事\n",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📋 {target_name} 的連結資訊",
            description="角色的背景故事",
            color=discord.Color.purple()
        )
        
        # 分割長訊息
        if len(bg_info) > 2000:
            # 如果訊息太長，分割發送
            parts = []
            current_part = ""
            lines = bg_info.split('\n')
            
            for line in lines:
                if len(current_part) + len(line) + 1 < 2000:
                    current_part += line + '\n'
                else:
                    parts.append(current_part)
                    current_part = line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            # 發送第一部分
            embed.add_field(name="📖 詳細資訊", value=parts[0], inline=False)
            await ctx.send(embed=embed)
            
            # 發送剩餘部分
            for i, part in enumerate(parts[1:], 2):
                embed2 = discord.Embed(
                    title=f"📋 {target_name} 的連結資訊續 {i})",
                    description=part,
                    color=discord.Color.purple()
                )
                await ctx.send(embed=embed2)
        else:
            embed.add_field(name="📖 詳細資訊", value=bg_info, inline=False)
            await ctx.send(embed=embed)
    
    else:
        # 顯示幫助
        embed = discord.Embed(
            title="🔗 角色連結系統",
            description="將背景故事和事件連結到特定角色",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="可用命令",
            value="""
            **!bind list** - 列出已連結的角色
            **!bind background [角色] [背景ID]** - 連結背景故事
            **!bind info [角色]** - 查看角色連結資訊
            """,
            inline=False
        )
        
        embed.add_field(
            name="💡 使用流程",
            value="""
            1. 先創建角色、背景故事和事件
            2. 將背景故事連結到角色
            3. 查看角色的發展歷程
            """,
            inline=False
        )
        await ctx.send(embed=embed)

@bot.command(name="character")
async def character_detail_command(ctx, character_name: str = None):
    """查看角色完整資訊（包含連結內容）"""
    
    if not character_name:
        await ctx.send("❌ 請提供角色名稱，例如: `!character 林秘書`")
        return
    
    # 查找角色
    all_characters = bot.virtual_society.get_all_characters()
    target_character = None
    character_key = None
    
    for key, char in all_characters.items():
        if char.name == character_name:
            target_character = char
            character_key = key
            break
    
    if not target_character:
        await ctx.send(f"❌ 找不到角色: {character_name}")
        return
    
    # 獲取角色提示
    enhanced_prompt = bot.virtual_society.get_enhanced_character_prompt(character_key)
    
    # 獲取背景資訊
    bg_info = bot.virtual_society.get_character_background_info(character_name)
    
    embed = discord.Embed(
        title=f"🎭 角色詳細資訊: {target_character.name}",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="👤 名稱", value=target_character.name, inline=True)
    embed.add_field(name="🎓 職業", value=target_character.profession, inline=True)
    embed.add_field(name="🎂 年齡", value=f"{target_character.age}歲", inline=True)
    embed.add_field(name="⚧️ 性別", value=target_character.gender, inline=True)
    embed.add_field(name="✨ 性格", value=target_character.personality, inline=True)
    embed.add_field(name="💬 說話風格", value=target_character.speech_style, inline=True)
    
    if target_character.values:
        embed.add_field(name="⭐ 價值觀", value=", ".join(target_character.values), inline=False)
    
    if target_character.interests:
        embed.add_field(name="🎯 興趣", value=", ".join(target_character.interests), inline=False)
    
    # 背景故事
    if target_character.background:
        embed.add_field(name="📖 基本背景", value=target_character.background[:200] + "...", inline=False)
    
    # 連結內容
    if bg_info:
        lines = bg_info.split('\n')
        binding_preview = "\n".join(lines[:10])  # 前10行
        if len(lines) > 10:
            binding_preview += "\n..."
        
        embed.add_field(name="🔗 連結內容", value=binding_preview, inline=False)
    
    embed.add_field(
        name="💬 使用方式",
        value=f"""
        對話: `!sandbox` 選擇 **{target_character.name}**
        連結: `!bind background {target_character.name}`
        詳細: `!bind info {target_character.name}`
        """,
        inline=False
    )
    
    await ctx.send(embed=embed)
    
    # 如果有更多的連結內容，發送第二部分
    if bg_info and len(bg_info) > 1000:
        remaining = bg_info[1000:]
        if len(remaining) > 1000:
            remaining = remaining[:1000] + "..."
        
        embed2 = discord.Embed(
            title=f"📋 {target_character.name} 的詳細背景",
            description=remaining,
            color=discord.Color.dark_purple()
        )
        await ctx.send(embed=embed2)
