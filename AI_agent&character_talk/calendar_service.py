# calendar_service.py
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime as dt
import pytz
from jsonschema import validate

SCOPES = ['https://www.googleapis.com/auth/calendar']


# JSON Schema 驗證
CALENDAR_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "date": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
        "start": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
        "end": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"},
    },
    "required": ["title", "date", "start", "end"]
}


class CalendarService:
    def __init__(self, credentials_path, timezone="Asia/Taipei"):
        self.credentials_path = credentials_path
        self.timezone = timezone
        self.service = self._authenticate()

    # --------------------------
    # Google Calendar 認證流程
    # --------------------------
    def _authenticate(self):
        """建立 Google Calendar API 認證"""

        creds = None

        # ① 若已有 token.json → 讀入
        if os.path.exists("token.json"):
            try:
                with open("token.json", "r") as token:
                    creds = Credentials.from_authorized_user_info(
                        json.load(token), SCOPES
                    )
            except Exception:
                print("⚠️ token.json 已損毀，將重新生成。")
                creds = None

        # ② 如果 token 無效 → 刷新或重新登入
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("🔁 Google Token 已刷新。")
                except Exception as e:
                    print(f"❌ Token 刷新失敗：{e}")
                    creds = None

            if not creds:
                # ③ 必須第一次登入（只需執行一次）
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )

                print("\n🌐 請開啟瀏覽器授權 Google Calendar！")
                creds = flow.run_local_server(port=8080)
                print("✅ Google Calendar 授權完成！")

            # ④ 儲存 token.json
            with open("token.json", "w") as token:
                token.write(creds.to_json())
                print("💾 新 token.json 已儲存。")

        # ⑤ 建立 Google Calendar API 客戶端
        service = build("calendar", "v3", credentials=creds)
        return service

    # --------------------------
    # 時間格式
    # --------------------------
    def _to_rfc3339(self, date_str, time_str):
        """轉換成 RFC3339（Google 日曆格式）"""
        y, m, d = map(int, date_str.split("-"))
        hh, mm = map(int, time_str.split(":"))

        tz = pytz.timezone(self.timezone)
        dt_obj = tz.localize(dt.datetime(y, m, d, hh, mm))

        return dt_obj.isoformat()

    # --------------------------
    # 建立事件
    # --------------------------
    def create_event(self, calendar_id, spec):
        """建立日曆事件"""

        # 驗證 spec 是否符合 Schema
        validate(instance=spec, schema=CALENDAR_SCHEMA)

        event = {
            "summary": spec["title"],
            "start": {
                "dateTime": self._to_rfc3339(spec["date"], spec["start"]),
                "timeZone": self.timezone,
            },
            "end": {
                "dateTime": self._to_rfc3339(spec["date"], spec["end"]),
                "timeZone": self.timezone,
            },
        }

        # 寫入 Google Calendar
        created = self.service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        return {
            "htmlLink": created["htmlLink"],
            "summary": created["summary"],
            "start": created["start"],
            "end": created["end"]
        }

    # --------------------------
    # 列出事件
    # --------------------------
    def list_events(self, calendar_id, max_results=10):
        """列出近期事件"""

        now = dt.datetime.utcnow().isoformat() + "Z"

        results = self.service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime"
        ).execute()

        return results.get("items", [])
