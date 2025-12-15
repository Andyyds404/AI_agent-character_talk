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
# 日曆功能命令
# ============================

@bot.command(name="add")
async def add_event(ctx, *, description):
    """添加日曆事件 - LangChain 版本（支援多事件）"""
    
    if not bot.calendar_service:
        await ctx.send("❌ 日曆服務不可用")
        return
    
    try:
        # 使用 LangChain 解析輸入
        await ctx.send("🤖 正在使用 LangChain 解析您的描述...")
        
        # 使用 process_multiple_events 方法
        result = bot.calendar_assistant.process_multiple_events(description)
        
        if not result["success"]:
            await ctx.send(f"❌ LangChain 解析錯誤: {result.get('error', '未知錯誤')}")
            return
        
        events_data = result["events"]
        
        if result["mode"] == "multi" and len(events_data) > 1:
            # 多事件處理
            embed = discord.Embed(
                title="🤖 LangChain 多事件解析結果",
                description=f"偵測到 **{len(events_data)}** 個事件",
                color=discord.Color.blue()
            )
            
            # 顯示所有事件
            for i, event in enumerate(events_data, 1):
                embed.add_field(
                    name=f"事件 {i}: {event['title']}",
                    value=f"日期: {event['date']}\n時間: {event['time_range']}",
                    inline=False
                )
            
            embed.set_footer(text="輸入 '!confirm' 建立所有事件，或 '!cancel' 取消")
            await ctx.send(embed=embed)
            
            # 儲存到用戶狀態
            bot.user_states[ctx.author.id] = {
                "events": events_data,
                "mode": "awaiting_confirmation"
            }
            
        else:
            # 單一事件處理
            event_data = events_data[0]
            
            # 轉換為字典
            spec = {
                "title": event_data["title"],
                "date": event_data["date"],
                "start": event_data["start"],
                "end": event_data["end"]
            }
            
            # 創建日曆事件
            try:
                event = bot.calendar_service.create_event(bot.calendar_id, spec)
                
                embed = discord.Embed(
                    title="✅ 事件已添加 (LangChain 解析)",
                    color=discord.Color.green()
                )
                
                embed.add_field(name="活動", value=spec['title'], inline=False)
                embed.add_field(name="日期", value=spec['date'], inline=True)
                embed.add_field(name="時間", value=f"{spec['start']} - {spec['end']}", inline=True)
                embed.add_field(name="日曆連結", value=f"[點擊查看]({event['htmlLink']})", inline=False)
                
                await ctx.send(embed=embed)
                
            except Exception as e:
                await ctx.send(f"❌ 建立日曆事件失敗: {str(e)}")
        
    except Exception as e:
        await ctx.send(f"❌ LangChain 解析錯誤: {str(e)}")

@bot.command(name="addmulti")
async def add_multi_event(ctx, *, description):
    """強制使用多事件模式添加日曆事件"""
    
    if not bot.calendar_service:
        await ctx.send("❌ 日曆服務不可用")
        return
    
    try:
        await ctx.send("🤖 正在使用 LangChain 多事件強制解析模式...")
        
        # 使用 process_multiple_events 並強制多事件模式
        result = bot.calendar_assistant.process_multiple_events(description, force_multi=True)
        
        if not result["success"]:
            await ctx.send(f"❌ LangChain 多事件解析錯誤: {result.get('error', '未知錯誤')}")
            return
        
        events_data = result["events"]
        
        embed = discord.Embed(
            title="🤖 LangChain 強制多事件解析結果",
            description=f"強制多事件模式偵測到 **{len(events_data)}** 個事件",
            color=discord.Color.purple()
        )
        
        for i, event in enumerate(events_data, 1):
            embed.add_field(
                name=f"事件 {i}: {event['title']}",
                value=f"日期: {event['date']}\n時間: {event['time_range']}",
                inline=False
            )
        
        embed.set_footer(text="輸入 '!confirm' 建立所有事件，或 '!cancel' 取消")
        await ctx.send(embed=embed)
        
        # 儲存到用戶狀態
        bot.user_states[ctx.author.id] = {
            "events": events_data,
            "mode": "awaiting_confirmation"
        }
        
    except Exception as e:
        await ctx.send(f"❌ LangChain 多事件解析錯誤: {str(e)}")

@bot.command(name="confirm")
async def confirm_events(ctx):
    """確認並建立多個事件"""
    
    user_id = ctx.author.id
    
    if user_id not in bot.user_states or bot.user_states[user_id]["mode"] != "awaiting_confirmation":
        await ctx.send("⚠️  沒有等待確認的事件")
        return
    
    if not bot.calendar_service:
        await ctx.send("❌ 日曆服務不可用")
        return
    
    events_data = bot.user_states[user_id]["events"]
    
    try:
        await ctx.send("🔄 正在建立事件到 Google Calendar...")
        
        success_count = 0
        failed_events = []
        created_events = []
        
        for event in events_data:
            try:
                spec = {
                    "title": event["title"],
                    "date": event["date"],
                    "start": event["start"],
                    "end": event["end"]
                }
                
                calendar_event = bot.calendar_service.create_event(bot.calendar_id, spec)
                success_count += 1
                created_events.append({
                    "title": event["title"],
                    "link": calendar_event['htmlLink']
                })
                
            except Exception as e:
                failed_events.append({
                    "title": event["title"],
                    "error": str(e)[:100]
                })
        
        # 清除用戶狀態
        del bot.user_states[user_id]
        
        # 顯示結果
        embed = discord.Embed(
            title="🎉 多事件建立完成",
            color=discord.Color.green() if len(failed_events) == 0 else discord.Color.orange()
        )
        
        embed.add_field(
            name="📊 結果統計",
            value=f"✅ 成功: {success_count} 個\n❌ 失敗: {len(failed_events)} 個\n📝 總數: {len(events_data)} 個",
            inline=False
        )
        
        if created_events:
            links_text = "\n".join([f"[{e['title']}]({e['link']})" for e in created_events[:3]])
            if len(created_events) > 3:
                links_text += f"\n...還有 {len(created_events)-3} 個事件"
            
            embed.add_field(
                name="🔗 已建立事件連結",
                value=links_text,
                inline=False
            )
        
        if failed_events:
            errors_text = "\n".join([f"**{e['title']}**: {e['error']}" for e in failed_events[:2]])
            if len(failed_events) > 2:
                errors_text += f"\n...還有 {len(failed_events)-2} 個失敗事件"
            
            embed.add_field(
                name="❌ 失敗事件",
                value=errors_text,
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ 事件建立失敗: {str(e)}")
        if user_id in bot.user_states:
            del bot.user_states[user_id]

@bot.command(name="cancel")
async def cancel_events(ctx):
    """取消待確認的事件"""
    
    user_id = ctx.author.id
    
    if user_id in bot.user_states and bot.user_states[user_id]["mode"] == "awaiting_confirmation":
        event_count = len(bot.user_states[user_id]["events"])
        del bot.user_states[user_id]
        await ctx.send(f"❌ 已取消 {event_count} 個待確認事件")
    else:
        await ctx.send("⚠️  沒有等待確認的事件")

@bot.command(name="events")
async def list_events(ctx, count: int = 5):
    """列出日曆事件"""
    if not bot.calendar_service:
        await ctx.send("❌ 日曆服務不可用")
        return
    
    try:
        events = bot.calendar_service.list_events(bot.calendar_id, count)
        
        if not events:
            embed = discord.Embed(
                title="📅 日曆事件",
                description="沒有找到近期事件",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title=f"📅 近期日曆事件 (LangChain 助理)",
            color=discord.Color.blue()
        )
        
        for i, event in enumerate(events, 1):
            summary = event.get('summary', '無標題')
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start:
                try:
                    start_dt = dt.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    time_str = start_dt.strftime("%m/%d %H:%M")
                except:
                    time_str = start
            else:
                time_str = f"全天 ({start})"
            
            embed.add_field(
                name=f"{i}. {summary}",
                value=time_str,
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ 錯誤: {str(e)}")

# # ============================
# # 虛擬沙盒命令
# # ============================

# @bot.command(name="sandbox")
# async def sandbox_command(ctx):
#     """啟動虛擬沙盒社會"""
    
#     class RoleButton(Button):
#         def __init__(self, role_key, character):
#             super().__init__(
#                 label=character.name[:15],
#                 style=discord.ButtonStyle.primary,
#                 emoji="🎭"
#             )
#             self.role_key = role_key
#             self.character = character
        
#         async def callback(self, interaction):
#             user_id = interaction.user.id
            
#             # 開始新對話
#             bot.active_conversations[user_id] = {
#                 "role_key": self.role_key,
#                 "character": self.character,
#                 "history": [],
#                 "current_scene": bot.virtual_society.current_scene
#             }
            
#             bot.current_mode = "sandbox"
#             bot.current_role = self.role_key
            
#             embed = discord.Embed(
#                 title=f"🎭 與 {self.character.name} 對話開始",
#                 description=f"**{self.character.profession}**\n\n性格: {self.character.personality}",
#                 color=discord.Color.purple()
#             )
            
#             embed.add_field(
#                 name="💬 使用方式",
#                 value="直接輸入訊息與角色對話\n輸入 `!stop` 結束對話",
#                 inline=False
#             )
            
#             embed.add_field(
#                 name="📍 當前場景",
#                 value=f"{bot.virtual_society.current_scene.location}\n氛圍: {bot.virtual_society.current_scene.atmosphere}",
#                 inline=True
#             )
            
#             await interaction.response.edit_message(
#                 content=f"🎮 虛擬沙盒社會",
#                 embed=embed,
#                 view=None
#             )
    
#     # 獲取所有角色
#     all_characters = bot.virtual_society.get_all_characters()
    
#     if not all_characters:
#         embed = discord.Embed(
#             title="🎮 虛擬沙盒社會",
#             description="還沒有任何角色，請先創建角色",
#             color=discord.Color.orange()
#         )
#         await ctx.send(embed=embed)
#         return
    
#     # 創建分類選擇
#     embed = discord.Embed(
#         title="🎮 虛擬沙盒社會",
#         description="選擇角色分類開始對話：",
#         color=discord.Color.purple()
#     )
    
#     view = View()
    
#     # 預設角色按鈕
#     default_chars = {k: v for k, v in all_characters.items() if not k.startswith('custom_')}
#     if default_chars:
#         default_button = Button(
#             label="📦 預設角色",
#             style=discord.ButtonStyle.primary,
#             emoji="📦",
#             custom_id="default_chars"
#         )
#         view.add_item(default_button)
    
#     # 自定義角色按鈕
#     custom_chars = {k: v for k, v in all_characters.items() if k.startswith('custom_')}
#     if custom_chars:
#         custom_button = Button(
#             label="🎨 自定義角色",
#             style=discord.ButtonStyle.success,
#             emoji="🎨",
#             custom_id="custom_chars"
#         )
#         view.add_item(custom_button)
    
#     await ctx.send(embed=embed, view=view)
    
#     # 處理按鈕點擊
#     @bot.event
#     async def on_interaction(interaction):
#         if interaction.data.get('custom_id') == 'default_chars':
#             await show_role_selection(interaction, default_chars, "📦 預設角色")
#         elif interaction.data.get('custom_id') == 'custom_chars':
#             await show_role_selection(interaction, custom_chars, "🎨 自定義角色")
    
#     async def show_role_selection(interaction, characters_dict, category_name):
#         """顯示角色選擇"""
#         embed = discord.Embed(
#             title=f"🎭 {category_name}",
#             description="請選擇一個角色：",
#             color=discord.Color.blue()
#         )
        
#         view = View()
        
#         # 添加角色按鈕
#         for role_key, character in list(characters_dict.items())[:12]:  # 限制最多12個
#             button = RoleButton(role_key, character)
#             view.add_item(button)
        
#         await interaction.response.edit_message(embed=embed, view=view)

# @bot.command(name="scene")
# async def scene_command(ctx, action: str = None, scene_name: str = None):
#     """場景管理命令"""
    
#     user_id = ctx.author.id
    
#     if user_id not in bot.active_conversations:
#         embed = discord.Embed(
#             title="⚠️  場景管理",
#             description="請先使用 `!sandbox` 選擇角色開始對話",
#             color=discord.Color.orange()
#         )
#         await ctx.send(embed=embed)
#         return
    
#     conversation = bot.active_conversations[user_id]
#     character = conversation["character"]
    
#     if action == "list":
#         # 列出可用場景
#         scenes = bot.virtual_society.scene_manager.get_available_scenes()
        
#         embed = discord.Embed(
#             title="🎭 可用場景列表",
#             description="請選擇一個場景切換：",
#             color=discord.Color.blue()
#         )
        
#         for key, location in scenes.items():
#             scene_info = bot.virtual_society.scene_manager.DEFAULT_SCENES[key]
#             embed.add_field(
#                 name=f"🔹 {key}",
#                 value=f"**{location}**\n氛圍: {scene_info.atmosphere}\n時間: {scene_info.time_period}",
#                 inline=True
#             )
        
#         embed.set_footer(text="使用 !scene change [場景名稱] 切換場景")
#         await ctx.send(embed=embed)
        
#     elif action == "change" and scene_name:
#         # 切換場景
#         result = bot.virtual_society.change_scene_command(scene_name)
        
#         if result.startswith("✅"):
#             # 更新對話中的場景
#             new_scene = bot.virtual_society.scene_manager.current_scene
#             conversation["current_scene"] = new_scene
            
#             embed = discord.Embed(
#                 title="🎬 場景切換成功",
#                 description=result,
#                 color=discord.Color.green()
#             )
            
#             # 記錄場景變更
#             conversation.get("history", []).append({
#                 "role": "system",
#                 "content": f"場景切換到 {new_scene.location}",
#                 "timestamp": dt.datetime.now().isoformat()
#             })
#         else:
#             embed = discord.Embed(
#                 title="❌ 場景切換失敗",
#                 description=result,
#                 color=discord.Color.red()
#             )
        
#         await ctx.send(embed=embed)
        
#     elif action == "info":
#         # 顯示當前場景資訊
#         scene_info = bot.virtual_society.get_current_scene_info()
        
#         embed = discord.Embed(
#             title="🎭 當前場景資訊",
#             color=discord.Color.purple()
#         )
        
#         embed.add_field(name="📍 地點", value=scene_info["location"], inline=True)
#         embed.add_field(name="⏰ 時間", value=scene_info["time_period"], inline=True)
#         embed.add_field(name="🌫️ 氛圍", value=scene_info["atmosphere"], inline=True)
        
#         await ctx.send(embed=embed)
        
#     else:
#         # 顯示幫助
#         embed = discord.Embed(
#             title="🎭 場景管理命令",
#             description="管理虛擬沙盒的場景設定",
#             color=discord.Color.blue()
#         )
        
#         embed.add_field(
#             name="可用命令",
#             value="""
#             **!scene list** - 列出所有可用場景
#             **!scene change [名稱]** - 切換到指定場景
#             **!scene info** - 顯示當前場景資訊
#             """,
#             inline=False
#         )
        
#         embed.add_field(
#             name="可用場景",
#             value="office, cafe, park, library, virtual_space",
#             inline=False
#         )
        
#         await ctx.send(embed=embed)

# @bot.command(name="help")
# async def help_command(ctx):
#     """顯示說明"""
    
#     embed = discord.Embed(
#         title="📚 **LangChain AI** 助理系統",
#         description="**完整角色綁定與故事系統**",
#         color=discord.Color.blue()
#     )
    
#     embed.add_field(
#         name="📅 日曆功能",
#         value="""```
#         !add [描述] - 添加事件
#         !events [數量] - 列出事件
#         !confirm - 確認建立事件
#         !cancel - 取消事件```""",
#         inline=True
#     )
    
#     embed.add_field(
#         name="🎮 虛擬沙盒",
#         value="""```
#         !sandbox - 啟動虛擬沙盒
#         !scene - 場景管理
#         !character [名稱] - 角色詳情```""",
#         inline=True
#     )
    
#     embed.add_field(
#         name="🔗 **角色綁定系統**",
#         value="""```
#         !bind - 綁定管理
#         !create - 創建內容
#         !list - 列出內容
#         !delete - 刪除內容```""",
#         inline=True
#     )
    
#     embed.add_field(
#         name="🛠️ 系統指令",
#         value="```!ping - 測試連線\n!stop - 結束對話\n!custom - 儀表板```",
#         inline=True
#     )

#     embed.add_field(
#         name="📝 **使用流程**",
#         value="""
#         1. `!create character` - 創建角色
#         2. `!create background` - 創建背景故事  
#         3. `!bind background [角色]` - 綁定背景
#         4. `!create event` - 創建事件
#         5. `!bind event [角色]` - 綁定事件
#         6. `!bind trigger [角色]` - 觸發事件
#         7. `!bind info [角色]` - 查看發展
#         """,
#         inline=False
#     )
    
#     embed.set_footer(text="打造深度角色扮演體驗 | 每個角色都有獨特的故事")
    
#     await ctx.send(embed=embed)

# @bot.command(name="ping")
# async def ping(ctx):
#     """測試連線"""
#     latency = round(bot.latency * 1000)
#     await ctx.send(f"🏓 Pong! LangChain 系統延遲: {latency}ms")

# @bot.command(name="stop")
# async def stop_command(ctx):
#     """停止當前對話"""
#     user_id = ctx.author.id
    
#     if user_id in bot.active_conversations:
#         role_name = bot.active_conversations[user_id]["character"].profession
#         del bot.active_conversations[user_id]
#         await ctx.send(f"✅ 已結束與 {role_name} 的對話")
#     else:
#         await ctx.send("⚠️  沒有正在進行的對話")

# @bot.command(name="mode")
# async def mode_command(ctx):
#     """顯示當前模式"""
#     embed = discord.Embed(
#         title="🎮 系統模式狀態",
#         color=discord.Color.blue()
#     )
    
#     if bot.current_mode == "sandbox" and bot.current_role:
#         character = bot.virtual_society.characters.get(bot.current_role)
#         if character:
#             embed.description = f"🎭 LangChain 虛擬沙盒模式\n角色: {character.profession}"
#         else:
#             embed.description = "🎭 LangChain 虛擬沙盒模式"
#     else:
#         embed.description = "📱 LangChain 正常模式"
    
#     await ctx.send(embed=embed)

# # ============================
# # 訊息處理
# # ============================

# @bot.event
# async def on_message(message):
#     """處理所有訊息"""
    
#     if message.author == bot.user:
#         return
    
#     user_id = message.author.id
    
#     # 檢查是否在沙盒對話中
#     if user_id in bot.active_conversations:
#         # 檢查停止指令
#         if message.content.lower() in ["停止", "結束", "exit", "stop", "quit", "bye"]:
#             del bot.active_conversations[user_id]
#             await message.channel.send("✅ 對話已結束，返回正常模式")
#             return
        
#         # 如果不是指令，視為對話
#         if not message.content.startswith("!"):
#             conversation = bot.active_conversations[user_id]
#             character = conversation["character"]
            
#             try:
#                 # 使用增強的角色回應生成
#                 response = bot.virtual_society.generate_role_response(
#                     conversation["role_key"], 
#                     message.content
#                 )
                
#                 # 更新對話歷史（包含背景發展）
#                 bot.virtual_society.update_conversation_with_background(
#                     conversation["role_key"],
#                     message.content,
#                     response
#                 )
                
#                 await message.channel.send(f"**{character.name}** ({character.profession}): {response}")
#             except Exception as e:
#                 await message.channel.send(f"❌ 對話錯誤: {str(e)}")
            
#             return
    
#     # 處理指令
#     await bot.process_commands(message)

# # 在 discord_bot_langchain.py 中添加自定義命令

# # ============================
# # 自定義功能命令
# # ============================

# @bot.command(name="create")
# async def create_command(ctx, item_type: str = None):
#     """創建自定義內容
    
#     用法:
#     !create character - 創建自定義角色
#     !create scene - 創建自定義場景
#     !create event - 創建自定義事件
#     !create background - 創建自定義背景故事
#     """
    
#     if item_type == "character":
#         embed = discord.Embed(
#             title="🎭 創建自定義角色",
#             description="請按照以下格式提供角色資訊：",
#             color=discord.Color.blue()
#         )
        
#         embed.add_field(
#             name="📝 格式",
#             value="""
#             ```
# 名稱: [角色名稱]
# 年齡: [年齡]
# 性別: [性別]
# 職業: [職業]
# 格: [性格特徵]
# 價值觀: [價值觀1, 價值觀2, ...]
# 說話風格: [說話風格]
# 背景故事: [背景故事]
# 興趣: [興趣1, 興趣2, ...]
#             ```""",
#             inline=False
#         )
        
#         embed.add_field(
#             name="📋 範例",
#             value="""
#             ```
# 名稱: 張老師
# 年齡: 35
# 性別: 男
# 職業: 數學教師
# 性格: 耐心、嚴謹、幽默
# 價值觀: 教育、誠實、成長
# 說話風格: 清晰、有條理、親切
# 背景故事: 有10年教學經驗的數學老師，熱愛教育事業
# 興趣: 數學、閱讀、登山
#             ```""",
#             inline=False
#         )
        
#         embed.set_footer(text="請複製格式並填寫後發送，我會為您創建角色")
        
#         await ctx.send(embed=embed)
        
#         # 等待用戶輸入
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=120.0, check=check)
#             await process_character_creation(ctx, msg.content)
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時，請重新使用 !create character")
            
#     elif item_type == "scene":
#         embed = discord.Embed(
#             title="🏢 創建自定義場景",
#             description="請按照以下格式提供場景資訊：",
#             color=discord.Color.green()
#         )
        
#         embed.add_field(
#             name="📝 格式",
#             value="""
#             ```
# 名稱: [場景名稱]
# 地點: [地點]
# 氛圍: [氛圍]
# 時間: [時間段]
# 描述: [詳細描述]
# 天氣: [天氣]
# 物件: [物件1, 物件2, ...]
# 聲音: [聲音1, 聲音2, ...]
#             ```""",
#             inline=False
#         )
        
#         embed.add_field(
#             name="📋 範例",
#             value="""
#             ```
# 名稱: 海邊咖啡廳
# 地點: 海濱咖啡廳
# 氛圍: 浪漫、放鬆
# 時間: 黃昏
# 描述: 位於海邊的咖啡廳，可以聽到海浪聲
# 天氣: 晴朗
# 物件: 咖啡桌, 沙發, 書籍, 畫作
# 聲音: 海浪聲, 輕音樂, 咖啡機聲
#             ```""",
#             inline=False
#         )
        
#         embed.set_footer(text="請複製格式並填寫後發送")
#         await ctx.send(embed=embed)
        
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=120.0, check=check)
#             await process_scene_creation(ctx, msg.content)
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時")
            
#     elif item_type == "event":
#         embed = discord.Embed(
#             title="✨ 創建自定義事件",
#             description="請按照以下格式提供事件資訊：",
#             color=discord.Color.purple()
#         )
        
#         embed.add_field(
#             name="📝 格式",
#             value="""
#             ```
# 標題: [事件標題]
# 描述: [事件描述]
# 類型: dialogue/conflict/discovery/decision/custom
# 觸發條件: [條件1, 條件2, ...]
# 涉及角色: [角色1, 角色2, ...]
# 地點: [發生地點]
# 選擇: [選項1:描述1, 選項2:描述2, ...]
#             ```""",
#             inline=False
#         )
        
#         embed.add_field(
#             name="📋 範例",
#             value="""
#             ```
# 標題: 意外的禮物
# 描述: 在抽屜裡發現了一個神秘的禮物盒
# 類型: discovery
# 觸發條件: 探索辦公室, 特定時間
# 涉及角色: 玩家, 同事
# 地點: 辦公室
# 選擇: 打開禮物:可能有好東西, 詢問同事:了解來源
#             ```""",
#             inline=False
#         )
        
#         embed.set_footer(text="請複製格式並填寫後發送")
#         await ctx.send(embed=embed)
        
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=120.0, check=check)
#             await process_event_creation(ctx, msg.content)
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時")
            
#     elif item_type == "background":
#         embed = discord.Embed(
#             title="📖 創建自定義背景故事",
#             description="請按照以下格式提供背景故事：",
#             color=discord.Color.gold()
#         )
        
#         embed.add_field(
#             name="📝 格式",
#             value="""
#             ```
# 標題: [背景標題]
# 內容: [背景故事內容]
#  角色: [相關角色名稱，可選]
#             ```""",
#             inline=False
#         )
        
#         embed.add_field(
#             name="📋 範例",
#             value="""
#             ```
# 標題: 王總監的過去
# 內容: 王總監年輕時曾在國外留學，主修商業管理。回國後從基層做起，憑藉出色的能力和努力，在10年內晉升為公司總監。他有一個幸福的家庭，但在事業上仍有更高的追求。
# 角色: 王總監
#             ```""",
#             inline=False
#         )
        
#         embed.set_footer(text="請複製格式並填寫後發送")
#         await ctx.send(embed=embed)
        
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=120.0, check=check)
#             await process_background_creation(ctx, msg.content)
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時")
            
#     else:
#         embed = discord.Embed(
#             title="🎨 自定義內容創建",
#             description="創建屬於您自己的虛擬沙盒內容",
#             color=discord.Color.blue()
#         )
        
#         embed.add_field(
#             name="可用命令",
#             value="""
#             **!create character** - 創建自定義角色
#             **!create scene** - 創建自定義場景
#             **!create event** - 創建自定義事件
#             **!create background** - 創建自定義背景故事
#             """,
#             inline=False
#         )
        
#         embed.add_field(
#             name="💡 提示",
#             value="每個命令都會提供詳細的格式說明，請按照說明填寫資訊",
#             inline=False
#         )
        
#         await ctx.send(embed=embed)

# async def process_character_creation(ctx, content: str):
#     """處理角色創建"""
#     try:
#         # 解析內容
#         data = {}
#         lines = content.split('\n')
#         for line in lines:
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 key = key.strip().lower()
#                 value = value.strip()
                
#                 if key in ['價值觀', '興趣']:
#                     data[key] = [v.strip() for v in value.split(',')]
#                 elif key == '年齡':
#                     data[key] = int(value)
#                 else:
#                     data[key] = value
        
#         # 創建角色
#         character = bot.virtual_society.create_custom_character(
#             name=data.get('名稱', '未命名'),
#             age=data.get('年齡', 25),
#             gender=data.get('性別', '未指定'),
#             profession=data.get('職業', '未指定'),
#             personality=data.get('性格', '中性'),
#             values=data.get('價值觀', []),
#             speech_style=data.get('說話風格', '普通'),
#             background=data.get('背景故事', '無'),
#             interests=data.get('興趣', [])
#         )
        
#         if character:
#             embed = discord.Embed(
#                 title="✅ 角色創建成功",
#                 description=f"已成功創建角色: **{character.name}**",
#                 color=discord.Color.green()
#             )
            
#             embed.add_field(name="👤 名稱", value=character.name, inline=True)
#             embed.add_field(name="🎭 職業", value=character.profession, inline=True)
#             embed.add_field(name="✨ 性格", value=character.personality, inline=True)
            
#             embed.add_field(
#                 name="💬 使用方式",
#                 value=f"使用 `!sandbox` 選擇角色，在自定義分類中找到 {character.name}",
#                 inline=False
#             )
            
#             await ctx.send(embed=embed)
#         else:
#             await ctx.send("❌ 角色創建失敗，請檢查格式是否正確")
            
#     except Exception as e:
#         await ctx.send(f"❌ 處理失敗: {str(e)}")

# async def process_scene_creation(ctx, content: str):
#     """處理場景創建"""
#     try:
#         # 解析內容
#         data = {}
#         lines = content.split('\n')
#         for line in lines:
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 key = key.strip().lower()
#                 value = value.strip()
                
#                 if key in ['物件', '聲音']:
#                     data[key] = [v.strip() for v in value.split(',')]
#                 else:
#                     data[key] = value
        
#         # 創建場景
#         scene = bot.virtual_society.create_custom_scene(
#             name=data.get('名稱', '未命名場景'),
#             location=data.get('地點', '未知地點'),
#             atmosphere=data.get('氛圍', '中性'),
#             time_period=data.get('時間', '現在'),
#             description=data.get('描述', ''),
#             weather=data.get('天氣', '晴朗'),
#             objects=data.get('物件', []),
#             background_sounds=data.get('聲音', [])
#         )
        
#         if scene:
#             embed = discord.Embed(
#                 title="✅ 場景創建成功",
#                 description=f"已成功創建場景: **{scene.name}**",
#                 color=discord.Color.green()
#             )
            
#             embed.add_field(name="📍 地點", value=scene.location, inline=True)
#             embed.add_field(name="⏰ 時間", value=scene.time_period, inline=True)
#             embed.add_field(name="🌫️ 氛圍", value=scene.atmosphere, inline=True)
            
#             if scene.description:
#                 embed.add_field(name="📝 描述", value=scene.description, inline=False)
            
#             embed.add_field(
#                 name="💬 使用方式",
#                 value=f"使用 `!scene change {scene.name}` 切換到此場景",
#                 inline=False
#             )
            
#             await ctx.send(embed=embed)
#         else:
#             await ctx.send("❌ 場景創建失敗，請檢查格式是否正確")
            
#     except Exception as e:
#         await ctx.send(f"❌ 處理失敗: {str(e)}")

# async def process_event_creation(ctx, content: str):
#     """處理事件創建"""
#     try:
#         # 解析內容
#         data = {}
#         lines = content.split('\n')
#         for line in lines:
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 key = key.strip().lower()
#                 value = value.strip()
                
#                 if key in ['觸發條件', '涉及角色']:
#                     data[key] = [v.strip() for v in value.split(',')]
#                 elif key == '選擇':
#                     choices = []
#                     for choice in value.split(','):
#                         if ':' in choice:
#                             action, desc = choice.split(':', 1)
#                             choices.append({"action": action.strip(), "description": desc.strip()})
#                     data[key] = choices
#                 else:
#                     data[key] = value
        
#         # 創建事件
#         event = bot.virtual_society.create_custom_event(
#             title=data.get('標題', '未命名事件'),
#             description=data.get('描述', ''),
#             event_type=data.get('類型', 'custom'),
#             trigger_conditions=data.get('觸發條件', []),
#             involved_characters=data.get('涉及角色', []),
#             location=data.get('地點', '未知地點'),
#             choices=data.get('選擇', [])
#         )
        
#         if event:
#             embed = discord.Embed(
#                 title="✅ 事件創建成功",
#                 description=f"已成功創建事件: **{event.title}**",
#                 color=discord.Color.green()
#             )
            
#             embed.add_field(name="🎯 標題", value=event.title, inline=True)
#             embed.add_field(name="📋 類型", value=event.event_type, inline=True)
#             embed.add_field(name="📍 地點", value=event.location, inline=True)
            
#             if event.description:
#                 embed.add_field(name="📝 描述", value=event.description[:100], inline=False)
            
#             embed.add_field(
#                 name="💾 存儲",
#                 value=f"事件已保存，可以在需要時觸發",
#                 inline=False
#             )
            
#             await ctx.send(embed=embed)
#         else:
#             await ctx.send("❌ 事件創建失敗，請檢查格式是否正確")
            
#     except Exception as e:
#         await ctx.send(f"❌ 處理失敗: {str(e)}")

# async def process_background_creation(ctx, content: str):
#     """處理背景故事創建"""
#     try:
#         # 解析內容
#         data = {}
#         lines = content.split('\n')
#         for line in lines:
#             if ':' in line:
#                 key, value = line.split(':', 1)
#                 key = key.strip().lower()
#                 value = value.strip()
#                 data[key] = value
        
#         # 創建背景故事
#         background = bot.virtual_society.create_custom_background(
#             title=data.get('標題', '未命名背景'),
#             content=data.get('內容', ''),
#             character_name=data.get('角色', '')
#         )
        
#         if background:
#             embed = discord.Embed(
#                 title="✅ 背景故事創建成功",
#                 description=f"已成功創建背景故事: **{background['title']}**",
#                 color=discord.Color.green()
#             )
            
#             embed.add_field(name="📖 標題", value=background['title'], inline=True)
            
#             if background.get('character_name'):
#                 embed.add_field(name="👤 相關角色", value=background['character_name'], inline=True)
            
#             if background.get('content'):
#                 embed.add_field(name="📝 內容", value=background['content'][:150] + "...", inline=False)
            
#             await ctx.send(embed=embed)
#         else:
#             await ctx.send("❌ 背景故事創建失敗")
            
#     except Exception as e:
#         await ctx.send(f"❌ 處理失敗: {str(e)}")

# @bot.command(name="list")
# async def list_command(ctx, item_type: str = None):
#     """列出自定義內容
    
#     用法:
#     !list characters - 列出所有角色（包含自定義）
#     !list scenes - 列出所有場景（包含自定義）
#     !list events - 列出所有事件
#     !list backgrounds - 列出所有背景故事
#     """
    
#     if item_type == "characters":
#         characters = bot.virtual_society.get_all_characters()
        
#         if not characters:
#             await ctx.send("📭 還沒有任何角色")
#             return
        
#         embed = discord.Embed(
#             title="🎭 所有角色列表",
#             description=f"共 {len(characters)} 個角色",
#             color=discord.Color.blue()
#         )
        
#         # 分組顯示
#         default_chars = []
#         custom_chars = []
        
#         for key, char in characters.items():
#             if key.startswith('custom_'):
#                 custom_chars.append(char)
#             else:
#                 default_chars.append(char)
        
#         if default_chars:
#             default_text = "\n".join([f"• **{char.name}** ({char.profession})" for char in default_chars[:5]])
#             embed.add_field(name="📦 預設角色", value=default_text, inline=False)
        
#         if custom_chars:
#             custom_text = "\n".join([f"• **{char.name}** ({char.profession})" for char in custom_chars[:5]])
#             embed.add_field(name="🎨 自定義角色", value=custom_text, inline=False)
            
#             if len(custom_chars) > 5:
#                 embed.set_footer(text=f"還有 {len(custom_chars)-5} 個自定義角色未顯示")
        
#         await ctx.send(embed=embed)
        
#     elif item_type == "scenes":
#         scenes = bot.virtual_society.get_all_scenes()
        
#         if not scenes:
#             await ctx.send("📭 還沒有任何場景")
#             return
        
#         embed = discord.Embed(
#             title="🏢 所有場景列表",
#             description=f"共 {len(scenes)} 個場景",
#             color=discord.Color.green()
#         )
        
#         # 分組顯示
#         default_scenes = []
#         custom_scenes = []
        
#         for name, scene in scenes.items():
#             if name in ["辦公室", "咖啡廳", "公園", "虛擬對話空間"]:
#                 default_scenes.append(scene)
#             else:
#                 custom_scenes.append(scene)
        
#         if default_scenes:
#             default_text = "\n".join([f"• **{scene.name}** - {scene.location}" for scene in default_scenes])
#             embed.add_field(name="📦 預設場景", value=default_text, inline=False)
        
#         if custom_scenes:
#             custom_text = "\n".join([f"• **{scene.name}** - {scene.location}" for scene in custom_scenes[:5]])
#             embed.add_field(name="🎨 自定義場景", value=custom_text, inline=False)
            
#             if len(custom_scenes) > 5:
#                 embed.set_footer(text=f"還有 {len(custom_scenes)-5} 個自定義場景未顯示")
        
#         await ctx.send(embed=embed)
        
#     elif item_type == "events":
#         events = bot.virtual_society.get_all_events()
        
#         if not events:
#             await ctx.send("📭 還沒有任何事件")
#             return
        
#         embed = discord.Embed(
#             title="✨ 所有事件列表",
#             description=f"共 {len(events)} 個事件",
#             color=discord.Color.purple()
#         )
        
#         for event_id, event in list(events.items())[:5]:
#             embed.add_field(
#                 name=f"🎯 {event.title}",
#                 value=f"類型: {event.event_type}\n地點: {event.location}\n描述: {event.description[:80]}...",
#                 inline=False
#             )
        
#         if len(events) > 5:
#             embed.set_footer(text=f"還有 {len(events)-5} 個事件未顯示")
        
#         await ctx.send(embed=embed)
        
#     elif item_type == "backgrounds":
#         backgrounds = bot.virtual_society.get_all_backgrounds()
        
#         if not backgrounds:
#             await ctx.send("📭 還沒有任何背景故事")
#             return
        
#         embed = discord.Embed(
#             title="📖 所有背景故事列表",
#             description=f"共 {len(backgrounds)} 個背景故事",
#             color=discord.Color.gold()
#         )
        
#         for bg_id, bg in list(backgrounds.items())[:5]:
#             title = bg.get('title', '未命名')
#             character = bg.get('character_name', '未指定角色')
            
#             embed.add_field(
#                 name=f"📚 {title}",
#                 value=f"角色: {character}\n內容: {bg.get('content', '')[:80]}...",
#                 inline=False
#             )
        
#         if len(backgrounds) > 5:
#             embed.set_footer(text=f"還有 {len(backgrounds)-5} 個背景故事未顯示")
        
#         await ctx.send(embed=embed)
        
#     else:
#         embed = discord.Embed(
#             title="📋 內容列表",
#             description="查看您創建的虛擬沙盒內容",
#             color=discord.Color.blue()
#         )
        
#         embed.add_field(
#             name="可用命令",
#             value="""
#             **!list characters** - 列出所有角色
#             **!list scenes** - 列出所有場景
#             **!list events** - 列出所有事件
#             **!list backgrounds** - 列出所有背景故事
#             """,
#             inline=False
#         )
        
#         embed.add_field(
#             name="💡 提示",
#             value="這些列表包含您創建的自定義內容和預設內容",
#             inline=False
#         )
        
#         await ctx.send(embed=embed)

# @bot.command(name="delete")
# async def delete_command(ctx, item_type: str = None, item_name: str = None):
#     """刪除自定義內容
    
#     用法:
#     !delete character [角色名稱] - 刪除自定義角色
#     !delete scene [場景名稱] - 刪除自定義場景
#     """
    
#     if not item_type or not item_name:
#         embed = discord.Embed(
#             title="🗑️ 刪除自定義內容",
#             description="刪除您創建的虛擬沙盒內容",
#             color=discord.Color.orange()
#         )
        
#         embed.add_field(
#             name="可用命令",
#             value="""
#             **!delete character [角色名稱]** - 刪除自定義角色
#             **!delete scene [場景名稱]** - 刪除自定義場景
            
#             ⚠️ **注意**: 刪除後無法恢復！
#             """,
#             inline=False
#         )
        
#         await ctx.send(embed=embed)
#         return
    
#     if item_type == "character":
#         # 確認刪除
#         embed = discord.Embed(
#             title="⚠️ 確認刪除角色",
#             description=f"您確定要刪除角色 **{item_name}** 嗎？",
#             color=discord.Color.red()
#         )
        
#         embed.add_field(
#             name="警告",
#             value="刪除後角色將永久消失，無法恢復！",
#             inline=False
#         )
        
#         embed.set_footer(text="輸入 '確認刪除' 繼續，輸入其他內容取消")
        
#         await ctx.send(embed=embed)
        
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=30.0, check=check)
            
#             if msg.content == "確認刪除":
#                 success = bot.virtual_society.delete_custom_character(item_name)
                
#                 if success:
#                     await ctx.send(f"✅ 已成功刪除角色: {item_name}")
#                 else:
#                     await ctx.send(f"❌ 刪除失敗，角色 '{item_name}' 不存在或不是自定義角色")
#             else:
#                 await ctx.send("❌ 刪除已取消")
                
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時，刪除已取消")
    
#     elif item_type == "scene":
#         # 確認刪除
#         embed = discord.Embed(
#             title="⚠️ 確認刪除場景",
#             description=f"您確定要刪除場景 **{item_name}** 嗎？",
#             color=discord.Color.red()
#         )
        
#         embed.add_field(
#             name="警告",
#             value="刪除後場景將永久消失，無法恢復！",
#             inline=False
#         )
        
#         embed.set_footer(text="輸入 '確認刪除' 繼續，輸入其他內容取消")
        
#         await ctx.send(embed=embed)
        
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=30.0, check=check)
            
#             if msg.content == "確認刪除":
#                 success = bot.virtual_society.delete_custom_scene(item_name)
                
#                 if success:
#                     await ctx.send(f"✅ 已成功刪除場景: {item_name}")
#                 else:
#                     await ctx.send(f"❌ 刪除失敗，場景 '{item_name}' 不存在或不是自定義場景")
#             else:
#                 await ctx.send("❌ 刪除已取消")
                
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時，刪除已取消")
    
#     else:
#         await ctx.send("❌ 不支援的刪除類型")

# @bot.command(name="custom")
# async def custom_dashboard(ctx):
#     """自定義內容儀表板"""
    
#     embed = discord.Embed(
#         title="🎨 自定義內容儀表板",
#         description="管理您的虛擬沙盒自定義內容",
#         color=discord.Color.blue()
#     )
    
#     # 獲取統計數據
#     characters = bot.virtual_society.get_all_characters()
#     scenes = bot.virtual_society.get_all_scenes()
#     events = bot.virtual_society.get_all_events()
#     backgrounds = bot.virtual_society.get_all_backgrounds()
    
#     # 計算自定義數量
#     custom_char_count = len([c for c in characters.values() if c.name.startswith('custom_')])
#     custom_scene_count = len([s for s in scenes.values() if s.name not in ["辦公室", "咖啡廳", "公園", "虛擬對話空間"]])
    
#     embed.add_field(
#         name="📊 內容統計",
#         value=f"""
#         • **角色**: {len(characters)} 個 ({custom_char_count} 個自定義)
#         • **場景**: {len(scenes)} 個 ({custom_scene_count} 個自定義)
#         • **事件**: {len(events)} 個
#         • **背景故事**: {len(backgrounds)} 個
#         """,
#         inline=False
#     )
    
#     embed.add_field(
#         name="🎯 創建命令",
#         value="""
#         **!create character** - 創建角色
#         **!create scene** - 創建場景
#         **!create event** - 創建事件
#         **!create background** - 創建背景故事
#         """,
#         inline=True
#     )
    
#     embed.add_field(
#         name="📋 查看命令",
#         value="""
#         **!list characters** - 查看角色
#         **!list scenes** - 查看場景
#         **!list events** - 查看事件
#         **!list backgrounds** - 查看背景
#         """,
#         inline=True
#     )
    
#     embed.add_field(
#         name="🗑️ 管理命令",
#         value="""
#         **!delete character** - 刪除角色
#         **!delete scene** - 刪除場景
#         """,
#         inline=False
#     )
    
#     embed.add_field(
#         name="💡 使用提示",
#         value="""
#         1. 創建時請仔細按照格式填寫
#         2. 所有內容都會自動保存
#         3. 可以隨時查看和刪除
#         4. 重啟機器人後內容仍然存在
#         """,
#         inline=False
#     )
    
#     embed.set_footer(text="盡情發揮創意，打造屬於您的虛擬世界！")
    
#     await ctx.send(embed=embed)

# @bot.command(name="bind")
# async def bind_command(ctx, action: str = None, target_name: str = None, target_type: str = None):
#     """綁定背景故事和事件到角色
    
#     用法:
#     !bind list - 列出已綁定的角色
#     !bind background [角色名稱] [背景ID] - 綁定背景故事
#     !bind event [角色名稱] [事件ID] - 綁定事件
#     !bind info [角色名稱] - 查看角色綁定資訊
#     !bind suggest [角色名稱] - 獲取建議事件
#     !bind trigger [角色名稱] [事件ID] - 觸發角色事件
#     """
    
#     if action == "list":
#         # 列出已綁定的角色
#         characters_with_bg = bot.virtual_society.get_character_with_backgrounds()
        
#         if not characters_with_bg:
#             embed = discord.Embed(
#                 title="📭 綁定角色列表",
#                 description="還沒有任何角色被綁定背景故事或事件",
#                 color=discord.Color.blue()
#             )
#             await ctx.send(embed=embed)
#             return
        
#         embed = discord.Embed(
#             title="📋 已綁定角色列表",
#             description=f"共 {len(characters_with_bg)} 個角色有綁定內容",
#             color=discord.Color.blue()
#         )
        
#         for char_info in characters_with_bg:
#             char = char_info["character"]
#             embed.add_field(
#                 name=f"🎭 {char.name} ({char.profession})",
#                 value=f"背景故事: {char_info['background_count']}個\n專屬事件: {char_info['event_count']}個\n使用: `!bind info {char.name}`",
#                 inline=False
#             )
        
#         await ctx.send(embed=embed)
        
#     elif action == "background" and target_name:
#         # 綁定背景故事到角色
#         # 首先讓用戶選擇背景故事
#         backgrounds = bot.virtual_society.get_all_backgrounds()
        
#         if not backgrounds:
#             await ctx.send("📭 還沒有創建任何背景故事，請先使用 `!create background` 創建")
#             return
        
#         # 檢查角色是否存在
#         all_characters = bot.virtual_society.get_all_characters()
#         character_exists = False
#         for char in all_characters.values():
#             if char.name == target_name:
#                 character_exists = True
#                 break
        
#         if not character_exists:
#             await ctx.send(f"❌ 角色 '{target_name}' 不存在")
#             return
        
#         # 顯示可用背景故事
#         embed = discord.Embed(
#             title="📖 選擇背景故事",
#             description=f"為角色 **{target_name}** 選擇要綁定的背景故事：",
#             color=discord.Color.purple()
#         )
        
#         for bg_id, bg in list(backgrounds.items())[:5]:
#             title = bg.get('title', '未命名')
#             content_preview = bg.get('content', '')[:80] + "..." if len(bg.get('content', '')) > 80 else bg.get('content', '')
            
#             embed.add_field(
#                 name=f"📚 {title}",
#                 value=f"ID: `{bg_id}`\n內容: {content_preview}",
#                 inline=False
#             )
        
#         embed.set_footer(text="請輸入背景故事的 ID 進行綁定")
#         await ctx.send(embed=embed)
        
#         # 等待用戶輸入背景ID
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=60.0, check=check)
#             background_id = msg.content.strip()
            
#             if background_id in backgrounds:
#                 # 綁定背景故事
#                 story_id = bot.virtual_society.bind_background_to_character(
#                     target_name, 
#                     backgrounds[background_id]
#                 )
                
#                 embed = discord.Embed(
#                     title="✅ 背景故事綁定成功",
#                     description=f"已將背景故事綁定到角色 **{target_name}**",
#                     color=discord.Color.green()
#                 )
                
#                 bg = backgrounds[background_id]
#                 embed.add_field(name="📖 背景標題", value=bg.get('title', '未命名'), inline=True)
#                 embed.add_field(name="🎭 綁定角色", value=target_name, inline=True)
#                 embed.add_field(name="🔗 故事ID", value=story_id, inline=True)
                
#                 embed.set_footer(text="角色現在會記得這個背景故事")
#                 await ctx.send(embed=embed)
#                 bot.virtual_society.bind_background_to_character(target_name, backgrounds[background_id])
    
#             else:
#                 await ctx.send("❌ 找不到指定的背景故事ID")
                
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時")
    
#     elif action == "event" and target_name and target_type:
#         # 綁定事件到角色
#         events = bot.virtual_society.get_all_events()
        
#         if not events:
#             await ctx.send("📭 還沒有創建任何事件，請先使用 `!create event` 創建")
#             return
        
#         # 檢查角色是否存在
#         all_characters = bot.virtual_society.get_all_characters()
#         character_exists = False
#         for char in all_characters.values():
#             if char.name == target_name:
#                 character_exists = True
#                 break
        
#         if not character_exists:
#             await ctx.send(f"❌ 角色 '{target_name}' 不存在")
#             return
        
#         # 顯示可用事件
#         embed = discord.Embed(
#             title="✨ 選擇事件",
#             description=f"為角色 **{target_name}** 選擇要綁定的事件：",
#             color=discord.Color.purple()
#         )
        
#         for event_id, event in list(events.items())[:5]:
#             embed.add_field(
#                 name=f"🎯 {event.title}",
#                 value=f"ID: `{event_id}`\n類型: {event.event_type}\n描述: {event.description[:80]}...",
#                 inline=False
#             )
        
#         embed.set_footer(text="請輸入事件的 ID 進行綁定")
#         await ctx.send(embed=embed)
        
#         # 等待用戶輸入事件ID
#         def check(m):
#             return m.author == ctx.author and m.channel == ctx.channel
        
#         try:
#             msg = await bot.wait_for('message', timeout=60.0, check=check)
#             event_id = msg.content.strip()
            
#             if event_id in events:
#                 # 綁定事件
#                 event_data = events[event_id].to_dict()
#                 success = bot.virtual_society.bind_event_to_character(target_name, event_data)
                
#                 if success:
#                     embed = discord.Embed(
#                         title="✅ 事件綁定成功",
#                         description=f"已將事件綁定到角色 **{target_name}**",
#                         color=discord.Color.green()
#                     )
                    
#                     event = events[event_id]
#                     embed.add_field(name="🎯 事件標題", value=event.title, inline=True)
#                     embed.add_field(name="🎭 綁定角色", value=target_name, inline=True)
#                     embed.add_field(name="📋 事件類型", value=event.event_type, inline=True)
                    
#                     embed.set_footer(text="使用 !bind trigger 觸發事件")
#                     await ctx.send(embed=embed)
#                 else:
#                     await ctx.send("❌ 事件綁定失敗")
#             else:
#                 await ctx.send("❌ 找不到指定的事件ID")
                
#         except asyncio.TimeoutError:
#             await ctx.send("⏰ 操作超時")
    
#     elif action == "info" and target_name:
#         # 查看角色綁定資訊
#         bg_info = bot.virtual_society.get_character_background_info(target_name)
        
#         if not bg_info:
#             embed = discord.Embed(
#                 title=f"📭 {target_name} 的綁定資訊",
#                 description="該角色還沒有綁定任何背景故事或事件",
#                 color=discord.Color.blue()
#             )
            
#             embed.add_field(
#                 name="💡 建議",
#                 value=f"使用 `!bind background {target_name}` 綁定背景故事\n使用 `!bind event {target_name}` 綁定事件",
#                 inline=False
#             )
            
#             await ctx.send(embed=embed)
#             return
        
#         embed = discord.Embed(
#             title=f"📋 {target_name} 的綁定資訊",
#             description="角色的背景故事和專屬事件",
#             color=discord.Color.purple()
#         )
        
#         # 分割長訊息
#         if len(bg_info) > 2000:
#             # 如果訊息太長，分割發送
#             parts = []
#             current_part = ""
#             lines = bg_info.split('\n')
            
#             for line in lines:
#                 if len(current_part) + len(line) + 1 < 2000:
#                     current_part += line + '\n'
#                 else:
#                     parts.append(current_part)
#                     current_part = line + '\n'
            
#             if current_part:
#                 parts.append(current_part)
            
#             # 發送第一部分
#             embed.add_field(name="📖 詳細資訊", value=parts[0], inline=False)
#             await ctx.send(embed=embed)
            
#             # 發送剩餘部分
#             for i, part in enumerate(parts[1:], 2):
#                 embed2 = discord.Embed(
#                     title=f"📋 {target_name} 的綁定資訊 (續 {i})",
#                     description=part,
#                     color=discord.Color.purple()
#                 )
#                 await ctx.send(embed=embed2)
#         else:
#             embed.add_field(name="📖 詳細資訊", value=bg_info, inline=False)
#             await ctx.send(embed=embed)
    
#     elif action == "suggest" and target_name:
#         # 獲取建議事件
#         suggested_events = bot.virtual_society.get_suggested_events_for_character(target_name)
        
#         if not suggested_events:
#             embed = discord.Embed(
#                 title=f"✨ 為 {target_name} 的建議事件",
#                 description="暫時沒有適合這個角色的建議事件",
#                 color=discord.Color.blue()
#             )
            
#             embed.add_field(
#                 name="💡 建議",
#                 value="您可以先為角色綁定一些背景故事，系統會根據背景推薦合適的事件",
#                 inline=False
#             )
            
#             await ctx.send(embed=embed)
#             return
        
#         embed = discord.Embed(
#             title=f"✨ 為 {target_name} 推薦的事件",
#             description="以下事件可能適合這個角色：",
#             color=discord.Color.green()
#         )
        
#         for i, event in enumerate(suggested_events, 1):
#             embed.add_field(
#                 name=f"{i}. {event.title}",
#                 value=f"ID: `{event.id}`\n類型: {event.event_type}\n描述: {event.description[:80]}...\n使用: `!bind event {target_name} {event.id}`",
#                 inline=False
#             )
        
#         await ctx.send(embed=embed)
    
#     elif action == "trigger" and target_type and target_name:
#         # 觸發角色事件
#         event_context = bot.virtual_society.trigger_character_event(target_name, target_type)
        
#         if not event_context:
#             await ctx.send("❌ 事件觸發失敗，請檢查角色名稱和事件ID")
#             return
        
#         event = event_context["event"]
        
#         embed = discord.Embed(
#             title="🎭 角色事件觸發！",
#             description=f"**{event.title}**\n\n{event.description}",
#             color=discord.Color.gold()
#         )
        
#         embed.add_field(name="🎯 涉及角色", value=target_name, inline=True)
#         embed.add_field(name="📍 發生地點", value=event.location, inline=True)
#         embed.add_field(name="✨ 事件類型", value=event.event_type, inline=True)
        
#         if event.choices:
#             choices_text = "\n".join([f"• **{c['action']}**: {c['description']}" for c in event.choices])
#             embed.add_field(name="🤔 可選行動", value=choices_text, inline=False)
        
#         embed.set_footer(text="事件已觸發，角色的發展歷程已更新")
#         await ctx.send(embed=embed)
        
#         # 記錄到對話歷史
#         user_id = ctx.author.id
#         if user_id in bot.active_conversations:
#             conversation = bot.active_conversations[user_id]
#             conversation["history"].append({
#                 "role": "system",
#                 "content": f"觸發事件: {event.title}",
#                 "timestamp": dt.datetime.now().isoformat()
#             })
    
#     else:
#         # 顯示幫助
#         embed = discord.Embed(
#             title="🔗 角色綁定系統",
#             description="將背景故事和事件綁定到特定角色",
#             color=discord.Color.blue()
#         )
        
#         embed.add_field(
#             name="可用命令",
#             value="""
#             **!bind list** - 列出已綁定的角色
#             **!bind background [角色] [背景ID]** - 綁定背景故事
#             **!bind event [角色] [事件ID]** - 綁定事件
#             **!bind info [角色]** - 查看角色綁定資訊
#             **!bind suggest [角色]** - 獲取建議事件
#             **!bind trigger [角色] [事件ID]** - 觸發角色事件
#             """,
#             inline=False
#         )
        
#         embed.add_field(
#             name="💡 使用流程",
#             value="""
#             1. 先創建角色、背景故事和事件
#             2. 將背景故事綁定到角色
#             3. 為角色綁定相關事件
#             4. 在對話中觸發事件
#             5. 查看角色的發展歷程
#             """,
#             inline=False
#         )
        
#         embed.set_footer(text="讓角色擁有豐富的背景和故事線！")
#         await ctx.send(embed=embed)

# @bot.command(name="character")
# async def character_detail_command(ctx, character_name: str = None):
#     """查看角色完整資訊（包含綁定內容）"""
    
#     if not character_name:
#         await ctx.send("❌ 請提供角色名稱，例如: `!character 林秘書`")
#         return
    
#     # 查找角色
#     all_characters = bot.virtual_society.get_all_characters()
#     target_character = None
#     character_key = None
    
#     for key, char in all_characters.items():
#         if char.name == character_name:
#             target_character = char
#             character_key = key
#             break
    
#     if not target_character:
#         await ctx.send(f"❌ 找不到角色: {character_name}")
#         return
    
#     # 獲取增強的角色提示
#     enhanced_prompt = bot.virtual_society.get_enhanced_character_prompt(character_key)
    
#     # 獲取背景資訊
#     bg_info = bot.virtual_society.get_character_background_info(character_name)
    
#     embed = discord.Embed(
#         title=f"🎭 角色詳細資訊: {target_character.name}",
#         color=discord.Color.purple()
#     )
    
#     # 基本資訊
#     embed.add_field(name="👤 名稱", value=target_character.name, inline=True)
#     embed.add_field(name="🎓 職業", value=target_character.profession, inline=True)
#     embed.add_field(name="🎂 年齡", value=f"{target_character.age}歲", inline=True)
#     embed.add_field(name="⚧️ 性別", value=target_character.gender, inline=True)
#     embed.add_field(name="✨ 性格", value=target_character.personality, inline=True)
#     embed.add_field(name="💬 說話風格", value=target_character.speech_style, inline=True)
    
#     # 價值觀和興趣
#     if target_character.values:
#         embed.add_field(name="⭐ 價值觀", value=", ".join(target_character.values), inline=False)
    
#     if target_character.interests:
#         embed.add_field(name="🎯 興趣", value=", ".join(target_character.interests), inline=False)
    
#     # 背景故事
#     if target_character.background:
#         embed.add_field(name="📖 基本背景", value=target_character.background[:200] + "...", inline=False)
    
#     # 綁定內容
#     if bg_info:
#         # 只顯示部分綁定內容
#         lines = bg_info.split('\n')
#         binding_preview = "\n".join(lines[:10])  # 前10行
#         if len(lines) > 10:
#             binding_preview += "\n..."
        
#         embed.add_field(name="🔗 綁定內容", value=binding_preview, inline=False)
    
#     # 使用方式
#     embed.add_field(
#         name="💬 使用方式",
#         value=f"""
#         對話: `!sandbox` 選擇 **{target_character.name}**
#         綁定: `!bind background {target_character.name}`
#         事件: `!bind suggest {target_character.name}`
#         詳細: `!bind info {target_character.name}`
#         """,
#         inline=False
#     )
    
#     await ctx.send(embed=embed)
    
#     # 如果有更多的綁定內容，發送第二部分
#     if bg_info and len(bg_info) > 1000:
#         remaining = bg_info[1000:]
#         if len(remaining) > 1000:
#             remaining = remaining[:1000] + "..."
        
#         embed2 = discord.Embed(
#             title=f"📋 {target_character.name} 的詳細背景",
#             description=remaining,
#             color=discord.Color.dark_purple()
#         )
#         await ctx.send(embed=embed2)

# @bot.command(name="initialize")
# @commands.has_permissions(administrator=True)  # 僅管理員可使用
# async def initialize_system(ctx, reset_type: str = "soft"):
#     """初始化系統，恢復到初始狀態
    
#     參數:
#     !initialize soft - 僅清除對話歷史和記憶中的背景資料
#     !initialize hard - 清除所有自定義內容（角色、場景、事件、背景）
#     !initialize full - 完全重置，恢復到出廠狀態（謹慎使用）
    
#     注意：此操作無法恢復，請謹慎使用！
#     """
    
#     if reset_type not in ["soft", "hard", "full"]:
#         embed = discord.Embed(
#             title="❌ 錯誤的初始化類型",
#             description="請使用以下其中一種類型：\n• `soft` - 軟重置（僅記憶）\n• `hard` - 硬重置（自定義內容）\n• `full` - 完全重置（出廠狀態）",
#             color=discord.Color.red()
#         )
#         await ctx.send(embed=embed)
#         return
    
#     # 警告訊息
#     warning_level = {
#         "soft": "⚠️",
#         "hard": "⚠️⚠️",
#         "full": "⚠️⚠️⚠️"
#     }
    
#     warning_messages = {
#         "soft": "將清除所有對話歷史和記憶中的背景資料",
#         "hard": "將清除所有自定義內容（角色、場景、事件、背景）",
#         "full": "將完全重置系統，恢復到出廠狀態"
#     }
    
#     embed = discord.Embed(
#         title=f"{warning_level[reset_type]} 系統初始化確認",
#         description=f"**{warning_messages[reset_type]}**\n\n此操作無法恢復！",
#         color=discord.Color.orange()
#     )
    
#     embed.add_field(
#         name="影響範圍",
#         value=f"""
#         • 對話歷史: {'✅ 清除' if reset_type in ['soft', 'hard', 'full'] else '❌ 保留'}
#         • 背景資料: {'✅ 清除' if reset_type in ['soft', 'hard', 'full'] else '❌ 保留'}
#         • 自定義角色: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
#         • 自定義場景: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
#         • 自定義事件: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
#         • 系統設定: {'✅ 重置' if reset_type == 'full' else '❌ 保留'}
#         """,
#         inline=False
#     )
    
#     embed.add_field(
#         name="確認操作",
#         value="請輸入 `確認初始化` 繼續，或輸入其他內容取消",
#         inline=False
#     )
    
#     embed.set_footer(text="此操作需要管理員權限")
    
#     await ctx.send(embed=embed)
    
#     def check(m):
#         return m.author == ctx.author and m.channel == ctx.channel
    
#     try:
#         msg = await bot.wait_for('message', timeout=30.0, check=check)
        
#         if msg.content == "確認初始化":
#             # 顯示處理中
#             processing_embed = discord.Embed(
#                 title="🔄 系統初始化中...",
#                 description=f"正在執行 {reset_type} 重置",
#                 color=discord.Color.blue()
#             )
#             processing_msg = await ctx.send(embed=processing_embed)
            
#             try:
#                 # 執行初始化
#                 result = bot.virtual_society.initialize_system(reset_type)
                
#                 if result["success"]:
#                     # 清除相關的 Discord 狀態
#                     bot.active_conversations.clear()
#                     bot.user_states.clear()
#                     bot.current_mode = "normal"
#                     bot.current_role = None
                    
#                     success_embed = discord.Embed(
#                         title="✅ 系統初始化完成",
#                         description=result["message"],
#                         color=discord.Color.green()
#                     )
                    
#                     # 添加詳細結果
#                     details = result.get("details", {})
#                     details_text = ""
                    
#                     if "conversation_history" in details:
#                         details_text += f"• 對話歷史: {details['conversation_history']} 條記錄已清除\n"
                    
#                     if "active_events" in details:
#                         details_text += f"• 活動事件: {details['active_events']} 個已清除\n"
                    
#                     if "backgrounds" in details:
#                         bg = details["backgrounds"]
#                         details_text += f"• 背景故事: {bg.get('stories_cleared', 0)} 個已清除\n"
#                         details_text += f"• 個人事件: {bg.get('events_cleared', 0)} 個已清除\n"
#                         details_text += f"• 角色發展: {bg.get('arc_cleared', 0)} 條記錄已清除\n"
                    
#                     if "custom_content" in details:
#                         cc = details["custom_content"]
#                         details_text += f"• 自定義角色: {cc.get('characters_cleared', 0)} 個已清除\n"
#                         details_text += f"• 自定義場景: {cc.get('scenes_cleared', 0)} 個已清除\n"
#                         details_text += f"• 自定義事件: {cc.get('events_cleared', 0)} 個已清除\n"
#                         details_text += f"• 記憶背景: {cc.get('backgrounds_cleared', 0)} 個已清除\n"
                    
#                     if details_text:
#                         success_embed.add_field(
#                             name="📊 清除統計",
#                             value=details_text,
#                             inline=False
#                         )
                    
#                     success_embed.add_field(
#                         name="🔄 系統狀態",
#                         value="• 所有對話已結束\n• 用戶狀態已清除\n• 系統模式已重置\n• 虛擬沙盒已恢復初始狀態",
#                         inline=False
#                     )
                    
#                     await processing_msg.edit(embed=success_embed)
#                 else:
#                     error_embed = discord.Embed(
#                         title="❌ 初始化失敗",
#                         description=result.get("error", "未知錯誤"),
#                         color=discord.Color.red()
#                     )
#                     await processing_msg.edit(embed=error_embed)
                    
#             except Exception as e:
#                 error_embed = discord.Embed(
#                     title="❌ 初始化過程出錯",
#                     description=str(e),
#                     color=discord.Color.red()
#                 )
#                 await processing_msg.edit(embed=error_embed)
#         else:
#             await ctx.send("❌ 初始化已取消")
            
#     except asyncio.TimeoutError:
#         await ctx.send("⏰ 操作超時，初始化已取消")

# # ============================
# # 運行機器人
# # ============================

# def run_bot():
#     """運行機器人"""
#     token = os.getenv('DISCORD_TOKEN')
#     if not token:
#         print("❌ 錯誤: 未找到 DISCORD_TOKEN")
#         return
    
#     print("🤖 正在啟動 LangChain AI 助理機器人...")
#     bot.run(token)

# if __name__ == "__main__":
#     run_bot()