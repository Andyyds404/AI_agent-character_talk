# run_langchain.py
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    """主程式"""
    print("🚀 LangChain AI 助理機器人啟動")
    print("=" * 60)
    
    # 檢查必要條件
    checks = {
        "Discord Token": os.getenv('DISCORD_TOKEN'),
        "Groq API Key": os.getenv('GROQ_API_KEY'),
        "Google Credentials": os.path.exists('credentials.json'),
        # "LangChain 安裝": True  # 假設已安裝
    }
    
    print("🔍 系統檢查 (LangChain 版本):")
    for name, value in checks.items():
        status = "✅" if value else "❌"
        print(f"  {status} {name}")
    
    if not checks["Discord Token"]:
        print("\n❌ 錯誤：必須設置 DISCORD_TOKEN")
        return
    
    print("\n🔄 正在啟動 LangChain 版本...")    
    print("\n🎯 主要指令:")
    print("  !add [描述] - LangChain 智能解析")
    print("  !sandbox - LangChain 虛擬沙盒")
    print("  !help - 完整說明")
    
    try:
        # 測試 LangChain 導入
        from langchain_groq import ChatGroq
        print("\n✅ LangChain 導入測試成功")
        
        from bot_groooup import run_bot
        run_bot()
        
    except ImportError as e:
        print(f"\n❌ LangChain 依賴缺失: {e}")
        print("請安裝: pip install langchain langchain-groq langchain-community")
    except Exception as e:
        print(f"\n❌ 啟動錯誤: {e}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 機器人已停止")