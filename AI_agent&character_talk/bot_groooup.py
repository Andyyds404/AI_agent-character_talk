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
import bot_calendar
import bot_sandbox

load_dotenv()

@bot.command(name="help")
async def help_command(ctx):
    """顯示說明"""
    
    embed = discord.Embed(
        title="📚 **LangChain AI** 助理系統",
        description="**完整角色連結與故事系統**",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📅 日曆功能",
        value="""```
!add [描述] - 添加事件
!events [數量] - 列出事件
!confirm - 確認建立事件
!cancel - 取消事件```""",
        inline=True
    )
    
    embed.add_field(
        name="🎮 角色模擬沙盒",
        value="""```
!sandbox - 啟動角色模擬
!scene - 場景管理
!character [名稱] - 角色詳情
!bind - 連結管理
!create - 創建內容
!list - 列出內容
!delete - 刪除內容```""",
        inline=True
    )
    
    embed.add_field(
        name="🛠️ 系統指令",
        value="```!ping - 測試連線\n!stop - 結束對話\n!custom - 儀表板\n!initialize - 初始化```",
        inline=True
    )
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping(ctx):
    """測試連線"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! LangChain 系統延遲: {latency}ms")

@bot.command(name="initialize")
@commands.has_permissions(administrator=True)  # 僅管理員可使用
async def initialize_system(ctx, reset_type: str = None):
    """初始化系統，恢復到初始狀態
    
    參數:
    !initialize soft - 僅清除對話歷史和記憶中的背景資料
    !initialize hard - 清除所有自定義內容（角色、場景、事件、背景）
    !initialize full - 完全重置，恢復到出廠狀態（謹慎使用）
    
    注意：此操作無法恢復，請謹慎使用！
    """
    
    if reset_type not in ["soft", "hard", "full"]:
        embed = discord.Embed(
            title="❌ 錯誤的初始化類型",
            description="請使用以下其中一種類型：\n• `soft` - 軟重置（僅記憶）\n• `hard` - 硬重置（自定義內容）\n• `full` - 完全重置（出廠狀態）",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # 警告訊息
    warning_level = {
        "soft": "⚠️",
        "hard": "⚠️⚠️",
        "full": "⚠️⚠️⚠️"
    }
    
    warning_messages = {
        "soft": "將清除所有對話歷史和記憶中的背景資料",
        "hard": "將清除所有自定義內容（角色、場景、事件、背景）",
        "full": "將完全重置系統，恢復到出廠狀態"
    }
    
    embed = discord.Embed(
        title=f"{warning_level[reset_type]} 系統初始化確認",
        description=f"**{warning_messages[reset_type]}**\n\n此操作無法恢復！",
        color=discord.Color.orange()
    )
    
    embed.add_field(
        name="影響範圍",
        value=f"""
        • 對話歷史: {'✅ 清除' if reset_type in ['soft', 'hard', 'full'] else '❌ 保留'}
        • 背景資料: {'✅ 清除' if reset_type in ['soft', 'hard', 'full'] else '❌ 保留'}
        • 自定義角色: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
        • 自定義場景: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
        • 自定義事件: {'✅ 清除' if reset_type in ['hard', 'full'] else '❌ 保留'}
        • 系統設定: {'✅ 重置' if reset_type == 'full' else '❌ 保留'}
        """,
        inline=False
    )
    
    embed.add_field(
        name="確認操作",
        value="請輸入 `確認初始化` 繼續，或輸入其他內容取消",
        inline=False
    )
    
    embed.set_footer(text="此操作需要管理員權限")
    
    await ctx.send(embed=embed)
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        msg = await bot.wait_for('message', timeout=30.0, check=check)
        
        if msg.content == "確認初始化":
            # 顯示處理中
            processing_embed = discord.Embed(
                title="🔄 系統初始化中...",
                description=f"正在執行 {reset_type} 重置",
                color=discord.Color.blue()
            )
            processing_msg = await ctx.send(embed=processing_embed)
            
            try:
                # 執行初始化
                result = bot.virtual_society.initialize_system(reset_type)
                
                if result["success"]:
                    # 清除相關的 Discord 狀態
                    bot.active_conversations.clear()
                    bot.user_states.clear()
                    bot.current_mode = "normal"
                    bot.current_role = None
                    
                    success_embed = discord.Embed(
                        title="✅ 系統初始化完成",
                        description=result["message"],
                        color=discord.Color.green()
                    )
                    
                    # 添加詳細結果
                    details = result.get("details", {})
                    details_text = ""
                    
                    if "conversation_history" in details:
                        details_text += f"• 對話歷史: {details['conversation_history']} 條記錄已清除\n"
                    
                    if "active_events" in details:
                        details_text += f"• 活動事件: {details['active_events']} 個已清除\n"
                    
                    if "backgrounds" in details:
                        bg = details["backgrounds"]
                        details_text += f"• 背景故事: {bg.get('stories_cleared', 0)} 個已清除\n"
                        details_text += f"• 個人事件: {bg.get('events_cleared', 0)} 個已清除\n"
                        details_text += f"• 角色發展: {bg.get('arc_cleared', 0)} 條記錄已清除\n"
                    
                    if "custom_content" in details:
                        cc = details["custom_content"]
                        details_text += f"• 自定義角色: {cc.get('characters_cleared', 0)} 個已清除\n"
                        details_text += f"• 自定義場景: {cc.get('scenes_cleared', 0)} 個已清除\n"
                        details_text += f"• 自定義事件: {cc.get('events_cleared', 0)} 個已清除\n"
                        details_text += f"• 記憶背景: {cc.get('backgrounds_cleared', 0)} 個已清除\n"
                    
                    if details_text:
                        success_embed.add_field(
                            name="📊 清除統計",
                            value=details_text,
                            inline=False
                        )
                    
                    success_embed.add_field(
                        name="🔄 系統狀態",
                        value="• 所有對話已結束\n• 用戶狀態已清除\n• 系統模式已重置\n• 虛擬沙盒已恢復初始狀態",
                        inline=False
                    )
                    
                    await processing_msg.edit(embed=success_embed)
                else:
                    error_embed = discord.Embed(
                        title="❌ 初始化失敗",
                        description=result.get("error", "未知錯誤"),
                        color=discord.Color.red()
                    )
                    await processing_msg.edit(embed=error_embed)
                    
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ 初始化過程出錯",
                    description=str(e),
                    color=discord.Color.red()
                )
                await processing_msg.edit(embed=error_embed)
        else:
            await ctx.send("❌ 初始化已取消")
            
    except asyncio.TimeoutError:
        await ctx.send("⏰ 操作超時，初始化已取消")

def run_bot():
    """運行機器人"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ 錯誤: 未找到 DISCORD_TOKEN")
        return
    
    print("🤖 正在啟動 LangChain AI 助理機器人...")
    bot.run(token)

if __name__ == "__main__":
    run_bot()