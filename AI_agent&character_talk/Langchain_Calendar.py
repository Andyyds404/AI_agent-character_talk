# langchain_calendar.py
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import List, Optional
import datetime as dt
import pytz
from jsonschema import validate
import re


# =========================
# 1️⃣ 日曆事件資料模型
# =========================

class CalendarEvent(BaseModel):
    """單一日曆事件數據模型"""
    title: str = Field(description="事件標題")
    date: str = Field(description="日期，格式：YYYY-MM-DD")
    start: str = Field(description="開始時間，格式：HH:MM")
    end: str = Field(description="結束時間，格式：HH:MM")


class MultipleCalendarEvents(BaseModel):
    """多個日曆事件數據模型"""
    events: List[CalendarEvent] = Field(description="事件列表")
    count: int = Field(description="事件數量")


# =========================
# 2️⃣ 日曆助理主體
# =========================

class CalendarAssistant:
    """LangChain LCEL 日曆助理（支援多事件）"""

    def __init__(self, groq_api_key: str, timezone: str = "Asia/Taipei"):
        self.timezone = timezone

        # LLM（Groq）
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=groq_api_key,
            model_name="llama-3.1-8b-instant"
        )

        # 單一事件解析器
        self.single_parser = PydanticOutputParser(pydantic_object=CalendarEvent)
        
        # 多事件解析器
        self.multi_parser = PydanticOutputParser(pydantic_object=MultipleCalendarEvents)

        # 單一事件 Prompt
        single_system_template = """
            你是一個日曆助理，負責將自然語言轉換為結構化的日曆事件，請將以下行程轉為中文簡述。

            ⚠️ 要求規則：
            - 只能輸出 JSON
            - 不得輸出任何解釋文字
            - 將行程事件濃縮成五個字以內的事件標題，要求字詞有邏輯且合理
            - 不得加入多餘欄位
            - 若資訊不完整，請合理推斷

            重要提示：
            - 當前日期：{current_date}（以此為基準計算相對時間）
            - 當前時間：{current_time}
            - 如果用戶沒有指定具體日期，請使用「明天」或合理的推斷
            - 如果用戶沒有指定時間，請使用合理的預設時間（如 09:00-17:00）
            - 請確保時間合理（結束時間晚於開始時間）

            輸出範例：
            {{"title": "團隊會議", "date": "2024-12-14", "start": "14:00", "end": "15:00"}}

            {format_instructions}
            """
        
        # 多事件 Prompt
        multi_system_template = """
            你是一個日曆助理，負責將自然語言轉換為多個結構化的日曆事件。

            ⚠️ 要求規則：
            - 只能輸出 JSON
            - 不得輸出任何解釋文字
            - 分析用戶輸入，判斷是否包含多個獨立事件
            - 每個事件都應有自己的標題、日期和時間
            - 將每個行程事件濃縮成五個字以內的事件標題，要求字詞有邏輯且合理
            - 不得加入多餘欄位
            - 若資訊不完整，請合理推斷

            重要提示：
            - 當前日期：{current_date}（以此為基準計算相對時間）
            - 當前時間：{current_time}
            - 如果用戶沒有指定具體日期，請使用「明天」或合理的推斷
            - 如果用戶沒有指定時間，請使用合理的預設時間（如 09:00-17:00）
            - 請確保每個事件的時間合理（結束時間晚於開始時間）

            事件識別關鍵字：
            - 然後、接著、之後、另外、還有、以及、再來
            - 第一、第二、第三、首先、其次、最後
            - 早上、下午、晚上、中午、傍晚
            - 分隔符號：逗號、頓號、分號

            輸出範例：
            {{
                "events": [
                    {{"title": "團隊會議", "date": "2024-12-14", "start": "09:00", "end": "10:00"}},
                    {{"title": "客戶拜訪", "date": "2024-12-14", "start": "14:00", "end": "16:00"}}
                ],
                "count": 2
            }}

            {format_instructions}
            """

        self.single_prompt = ChatPromptTemplate.from_messages([
            ("system", single_system_template),
            ("human", "{user_input}")
        ])
        
        self.multi_prompt = ChatPromptTemplate.from_messages([
            ("system", multi_system_template),
            ("human", "{user_input}")
        ])

        # 創建兩個 Chain：單一事件和多事件
        self.single_chain = self.single_prompt | self.llm | self.single_parser
        self.multi_chain = self.multi_prompt | self.llm | self.multi_parser

    # =========================
    # 3️⃣ 對外使用介面
    # =========================

    def parse_input(self, user_input: str) -> CalendarEvent:
        """解析自然語言為單一日曆事件"""
        now = dt.datetime.now(pytz.timezone(self.timezone))
        
        inputs = {
            "user_input": user_input,
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M"),
            "format_instructions": self.single_parser.get_format_instructions()
        }

        try:
            event = self.single_chain.invoke(inputs)
            self._validate_event(event)
            return event
        except Exception as e:
            raise ValueError(f"❌ LangChain 解析錯誤: {e}")

    def parse_multiple_input(self, user_input: str) -> List[CalendarEvent]:
        """解析自然語言為多個日曆事件"""
        now = dt.datetime.now(pytz.timezone(self.timezone))
        
        inputs = {
            "user_input": user_input,
            "current_date": now.strftime("%Y-%m-%d"),
            "current_time": now.strftime("%H:%M"),
            "format_instructions": self.multi_parser.get_format_instructions()
        }

        try:
            result = self.multi_chain.invoke(inputs)
            for event in result.events:
                self._validate_event(event)
            return result.events
        except Exception as e:
            # 如果多事件解析失敗，嘗試單一事件
            try:
                single_event = self.parse_input(user_input)
                return [single_event]
            except:
                raise ValueError(f"❌ LangChain 多事件解析錯誤: {e}")

    def _has_multiple_events(self, text: str) -> bool:
        """判斷輸入是否可能包含多個事件"""
        # 檢查多事件關鍵字
        keywords = [
            # 序列詞
            "然後", "接著", "之後", "另外", "還有", "以及", "再來", "隨後",
            "第一", "第二", "第三", "首先", "其次", "最後", 
            # 時間詞
            "早上", "上午", "中午", "下午", "晚上", "傍晚", "深夜",
            "9點", "10點", "11點", "12點", "13點", "14點", "15點", "16點", "17點", "18點", "19點", "20點",
            # 分隔符
            "，", "、", "；", " ", "  ", "\n"
        ]
        
        # 檢查關鍵字
        for keyword in keywords:
            if keyword in text:
                return True
        
        # 檢查是否有多個時間段
        time_patterns = [
            r'\d{1,2}[:：]\d{2}',  # 12:30
            r'\d{1,2}點\d{1,2}分',  # 12點30分
            r'\d{1,2}點',           # 12點
        ]
        
        total_times = 0
        for pattern in time_patterns:
            matches = re.findall(pattern, text)
            total_times += len(matches)
            
            if total_times >= 2:  # 如果有兩個或更多時間點，可能是多事件
                return True
        
        return False

    # =========================
    # 4️⃣ 輸出驗證
    # =========================

    def _validate_event(self, event: CalendarEvent):
        """驗證輸出格式"""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
                "start": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
                "end": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"}
            },
            "required": ["title", "date", "start", "end"]
        }
        
        validate(instance=event.dict(), schema=schema)
    
    def process_multiple_events(self, user_input: str, force_multi: bool = False) -> dict:
        """處理多事件輸入並返回詳細結果"""
        try:
            if force_multi or self._has_multiple_events(user_input):
                # 解析多事件
                events = self.parse_multiple_input(user_input)
                mode = "multi"
            else:
                # 解析單一事件
                event = self.parse_input(user_input)
                events = [event]
                mode = "single"
            
            result = {
                "success": True,
                "mode": mode,
                "count": len(events),
                "events": [],
                "summary": f"成功解析 {len(events)} 個事件 ({mode}模式)"
            }
            
            for i, event in enumerate(events, 1):
                event_dict = event.dict()
                event_dict["index"] = i
                event_dict["time_range"] = f"{event.start} - {event.end}"
                result["events"].append(event_dict)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "count": 0,
                "events": []
            }


# =========================
# 5️⃣ 本地測試
# =========================

if __name__ == "__main__":
    from config import GROQ_API_KEY, TIMEZONE

    assistant = CalendarAssistant(
        groq_api_key=GROQ_API_KEY,
        timezone=TIMEZONE
    )

    test_inputs = [
        # 單一事件
        "明天下午三點到五點要跟老師開會",
        # 多事件（明顯分隔）
        "早上九點到十一點要開團隊會議，然後下午兩點到四點拜訪客戶",
        # 多事件（序列）
        "首先早上十點開會，接著下午兩點見客戶，最後晚上七點聚餐",
        # 多事件（時間段）
        "週一上午系統分析課，下午專案討論會",
        "12月25日早上家庭聚會，中午聖誕大餐，晚上交換禮物"
    ]

    for text in test_inputs:
        print(f"\n{'='*60}")
        print(f"🗣 使用者輸入：{text}")
        
        try:
            result = assistant.process_multiple_events(text)
            
            if result["success"]:
                print(f"✅ LangChain 解析成功：{result['summary']}")
                for event in result["events"]:
                    print(f"  {event['index']}. {event['title']}")
                    print(f"     日期：{event['date']}，時間：{event['time_range']}")
            else:
                print(f"❌ 解析失敗：{result['error']}")
                
        except Exception as e:
            print(f"❌ 錯誤：{e}")