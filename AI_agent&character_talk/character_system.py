import json
import os
import uuid
import shutil
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
import datetime as dt

@dataclass
class CharacterTrait:
    """角色特質"""
    name: str  # 角色名稱
    personality: str  # 性格特徵
    values: List[str]  # 價值觀
    speech_style: str  # 說話風格
    background: str  # 背景故事
    profession: str  # 職業/身份
    interests: List[str]  # 興趣愛好
    age: int = 25  # 年齡
    gender: str = "未指定"  # 性別
    relationships: Dict[str, str] = field(default_factory=dict)  # 關係網絡
    
    def to_prompt(self) -> str:
        """轉換為prompt"""
        relationships_text = ""
        if self.relationships:
            relationships_text = "\n關係: " + ", ".join([f"{k}: {v}" for k, v in self.relationships.items()])
        
        return f"""
        角色名稱: {self.name}
        年齡: {self.age}歲
        性別: {self.gender}
        職業/身份: {self.profession}
        性格特徵: {self.personality}
        價值觀: {', '.join(self.values)}
        說話風格: {self.speech_style}
        背景故事: {self.background}
        興趣愛好: {', '.join(self.interests)}{relationships_text}
        """
    
    def to_dict(self) -> Dict:
        """轉換為字典"""
        return asdict(self)

@dataclass
class SceneSetting:
    """場景設定"""
    name: str  # 場景名稱
    location: str  # 地點
    atmosphere: str  # 氛圍
    time_period: str  # 時間段
    description: str = ""  # 詳細描述
    weather: str = "晴朗"  # 天氣
    objects: List[str] = field(default_factory=list)  # 場景中的物件
    background_sounds: List[str] = field(default_factory=list)  # 背景聲音
    
    def to_prompt(self) -> str:
        """轉換為提示詞"""
        objects_text = f", 周圍有: {', '.join(self.objects)}" if self.objects else ""
        sounds_text = f", 背景聲音: {', '.join(self.background_sounds)}" if self.background_sounds else ""
        
        return f"""
        場景名稱: {self.name}
        地點: {self.location}
        時間: {self.time_period}
        天氣: {self.weather}
        氛圍: {self.atmosphere}
        描述: {self.description}{objects_text}{sounds_text}
        """
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class StoryEvent:
    """故事事件"""
    id: str
    title: str  # 事件標題
    description: str  # 事件描述
    event_type: str  # 事件類型: dialogue, conflict, discovery, decision, custom
    trigger_conditions: List[str]  # 觸發條件
    involved_characters: List[str]  # 涉及的角色
    location: str  # 發生地點
    choices: List[Dict[str, str]] = field(default_factory=list)  # 玩家選擇
    outcomes: List[str] = field(default_factory=list)  # 可能結果
    custom_data: Dict = field(default_factory=dict)  # 自定義數據
    
    def to_prompt(self) -> str:
        """轉換為提示詞"""
        choices_text = ""
        if self.choices:
            choices_text = "\n可選行動:\n" + "\n".join([f"• {c['action']}: {c['description']}" for c in self.choices])
        
        return f"""
        [事件: {self.title}]
        描述: {self.description}
        類型: {self.event_type}
        地點: {self.location}
        涉及角色: {', '.join(self.involved_characters)}
        觸發條件: {', '.join(self.trigger_conditions)}{choices_text}
        """
    
    def to_dict(self) -> Dict:
        return asdict(self)

class CustomizationManager:
    """自定義管理系統"""
    
    def __init__(self):
        self.custom_characters = {}
        self.custom_scenes = {}
        self.custom_events = {}
        self.custom_backgrounds = {}  # 保留背景故事記憶，但不保存檔案
        
        self._ensure_directories()
        self._load_custom_content()
    
    def _ensure_directories(self):
        directories = ['custom/characters', 'custom/scenes', 'custom/events']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def _load_custom_content(self):
        self._load_custom_characters()
        self._load_custom_scenes()
        self._load_custom_events()
        
        # 背景故事不從檔案載入，僅在記憶中
        print("✅ 背景故事系統初始化完成（記憶中）")
    
    def _load_custom_characters(self):
        """載入自定義角色"""
        character_dir = 'custom/characters'
        if os.path.exists(character_dir):
            for filename in os.listdir(character_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(character_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            character = CharacterTrait(**data)
                            self.custom_characters[character.name] = character
                            print(f"✅ 載入自定義角色: {character.name}")
                    except Exception as e:
                        print(f"❌ 載入角色 {filename} 失敗: {e}")
    
    def _load_custom_scenes(self):
        """載入自定義場景"""
        scene_dir = 'custom/scenes'
        if os.path.exists(scene_dir):
            for filename in os.listdir(scene_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(scene_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            scene = SceneSetting(**data)
                            self.custom_scenes[scene.name] = scene
                            print(f"✅ 載入自定義場景: {scene.name}")
                    except Exception as e:
                        print(f"❌ 載入場景 {filename} 失敗: {e}")
    
    def _load_custom_events(self):
        """載入自定義事件"""
        event_dir = 'custom/events'
        if os.path.exists(event_dir):
            for filename in os.listdir(event_dir):
                if filename.endswith('.json'):
                    try:
                        with open(os.path.join(event_dir, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            event = StoryEvent(**data)
                            self.custom_events[event.id] = event
                            print(f"✅ 載入自定義事件: {event.title}")
                    except Exception as e:
                        print(f"❌ 載入事件 {filename} 失敗: {e}")
    
    def save_custom_character(self, character: CharacterTrait) -> bool:
        """保存自定義角色"""
        try:
            filename = f"custom/characters/{character.name.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(character.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.custom_characters[character.name] = character
            print(f"✅ 保存自定義角色: {character.name}")
            return True
        except Exception as e:
            print(f"❌ 保存角色失敗: {e}")
            return False
    
    def save_custom_scene(self, scene: SceneSetting) -> bool:
        """保存自定義場景"""
        try:
            filename = f"custom/scenes/{scene.name.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(scene.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.custom_scenes[scene.name] = scene
            print(f"✅ 保存自定義場景: {scene.name}")
            return True
        except Exception as e:
            print(f"❌ 保存場景失敗: {e}")
            return False
    
    def save_custom_event(self, event: StoryEvent) -> bool:
        """保存自定義事件"""
        try:
            filename = f"custom/events/{event.id}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(event.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.custom_events[event.id] = event
            print(f"✅ 保存自定義事件: {event.title}")
            return True
        except Exception as e:
            print(f"❌ 保存事件失敗: {e}")
            return False
    
    def add_custom_background(self, background: Dict) -> bool:
        """添加自定義背景故事到記憶中"""
        try:
            background_id = background.get('id', str(uuid.uuid4())[:8])
            background['id'] = background_id
            self.custom_backgrounds[background_id] = background
            print(f"✅ 添加自定義背景到記憶: {background.get('title', '未命名')}")
            return True
        except Exception as e:
            print(f"❌ 添加背景失敗: {e}")
            return False
    
    def delete_custom_character(self, character_name: str) -> bool:
        """刪除自定義角色"""
        try:
            filename = f"custom/characters/{character_name.replace(' ', '_')}.json"
            if os.path.exists(filename):
                os.remove(filename)
                if character_name in self.custom_characters:
                    del self.custom_characters[character_name]
                print(f"✅ 刪除自定義角色: {character_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ 刪除角色失敗: {e}")
            return False
    
    def delete_custom_scene(self, scene_name: str) -> bool:
        """刪除自定義場景"""
        try:
            filename = f"custom/scenes/{scene_name.replace(' ', '_')}.json"
            if os.path.exists(filename):
                os.remove(filename)
                if scene_name in self.custom_scenes:
                    del self.custom_scenes[scene_name]
                print(f"✅ 刪除自定義場景: {scene_name}")
                return True
            return False
        except Exception as e:
            print(f"❌ 刪除場景失敗: {e}")
            return False
    
    def delete_custom_event(self, event_id: str) -> bool:
        """刪除自定義事件"""
        try:
            filename = f"custom/events/{event_id}.json"
            if os.path.exists(filename):
                os.remove(filename)
                if event_id in self.custom_events:
                    del self.custom_events[event_id]
                print(f"✅ 刪除自定義事件: {event_id}")
                return True
            return False
        except Exception as e:
            print(f"❌ 刪除事件失敗: {e}")
            return False
    
    def clear_all_custom_content(self) -> Dict[str, int]:
        """清除所有自定義內容"""
        results = {
            "characters_cleared": 0,
            "scenes_cleared": 0,
            "backgrounds_cleared": 0
        }
        
        try:
            # 清空記憶中的背景故事
            results["backgrounds_cleared"] = len(self.custom_backgrounds)
            self.custom_backgrounds.clear()
            print(f"✅ 清空記憶中的背景故事: {results['backgrounds_cleared']}個")
            
            # 清空自定義角色檔案
            character_dir = 'custom/characters'
            if os.path.exists(character_dir):
                files = [f for f in os.listdir(character_dir) if f.endswith('.json')]
                results["characters_cleared"] = len(files)
                for filename in files:
                    os.remove(os.path.join(character_dir, filename))
                print(f"✅ 清空自定義角色檔案: {results['characters_cleared']}個")
            
            # 清空自定義場景檔案
            scene_dir = 'custom/scenes'
            if os.path.exists(scene_dir):
                files = [f for f in os.listdir(scene_dir) if f.endswith('.json')]
                results["scenes_cleared"] = len(files)
                for filename in files:
                    os.remove(os.path.join(scene_dir, filename))
                print(f"✅ 清空自定義場景檔案: {results['scenes_cleared']}個")
            
            # 清空記憶中的自定義內容
            self.custom_characters.clear()
            self.custom_scenes.clear()
            
            print("✅ 所有自定義內容已清除")
            return results
            
        except Exception as e:
            print(f"❌ 清除自定義內容失敗: {e}")
            return results
    
    def get_all_custom_characters(self) -> Dict[str, CharacterTrait]:
        """獲取所有自定義角色"""
        return self.custom_characters.copy()
    
    def get_all_custom_scenes(self) -> Dict[str, SceneSetting]:
        """獲取所有自定義場景"""
        return self.custom_scenes.copy()
    
    def get_all_custom_backgrounds(self) -> Dict[str, Dict]:
        """獲取所有自定義背景"""
        return self.custom_backgrounds.copy()

class CharacterBackground:
    """角色背景故事綁定（記憶中）"""
    
    def __init__(self, character_name: str):
        self.character_name = character_name
        self.stories = []  # 相關的背景故事
        self.personal_events = []  # 個人專屬事件
        self.character_arc = []  # 角色發展歷程
        self.secrets = []  # 角色秘密
        self.motivations = []  # 動機和目標
    
    def add_story(self, story_title: str, story_content: str, story_id: str = None):
        """添加背景故事到記憶"""
        if story_id is None:
            story_id = str(uuid.uuid4())[:8]
        
        story = {
            "id": story_id,
            "title": story_title,
            "content": story_content,
            "added_at": dt.datetime.now().isoformat()
        }
        
        self.stories.append(story)
        return story_id
    
    def add_event(self, event: StoryEvent):
        """添加個人事件"""
        self.personal_events.append({
            "event": event,
            "added_at": dt.datetime.now().isoformat()
        })
    
    def add_to_character_arc(self, development: str):
        """添加角色發展"""
        self.character_arc.append({
            "development": development,
            "timestamp": dt.datetime.now().isoformat()
        })
    
    def clear_all_background_data(self):
        """清除所有背景資料"""
        stories_count = len(self.stories)
        events_count = len(self.personal_events)
        arc_count = len(self.character_arc)
        
        self.stories.clear()
        self.personal_events.clear()
        self.character_arc.clear()
        self.secrets.clear()
        self.motivations.clear()
        
        return {
            "stories_cleared": stories_count,
            "events_cleared": events_count,
            "arc_cleared": arc_count
        }
    
    def get_background_summary(self) -> str:
        """獲取背景摘要"""
        summary = f"角色: {self.character_name}\n"
        
        if self.stories:
            summary += f"\n📖 背景故事 ({len(self.stories)}個):\n"
            for story in self.stories[-3:]:  # 最近3個故事
                summary += f"  • {story['title']}: {story['content'][:50]}...\n"
        
        if self.personal_events:
            summary += f"\n✨ 個人事件 ({len(self.personal_events)}個):\n"
            for record in self.personal_events[-2:]:
                event = record["event"]
                summary += f"  • {event.title}: {event.description[:50]}...\n"
        
        if self.character_arc:
            summary += f"\n📈 角色發展:\n"
            for arc in self.character_arc[-2:]:
                summary += f"  • {arc['development']}\n"
        
        return summary
    
    def get_enhanced_prompt(self) -> str:
        """獲取增強提示詞（包含所有背景故事）"""
        enhanced_prompt = ""
        
        if self.stories:
            enhanced_prompt += "\n\n📖 角色背景故事:\n"
            for story in self.stories:
                enhanced_prompt += f"• {story['title']}: {story['content']}\n"
        
        if self.character_arc:
            enhanced_prompt += "\n📈 角色發展歷程:\n"
            for arc in self.character_arc:
                enhanced_prompt += f"• {arc['development']}\n"
        
        if self.secrets:
            enhanced_prompt += "\n🔒 角色秘密:\n"
            for secret in self.secrets:
                enhanced_prompt += f"• {secret}\n"
        
        if self.motivations:
            enhanced_prompt += "\n🎯 角色動機:\n"
            for motivation in self.motivations:
                enhanced_prompt += f"• {motivation}\n"
        
        return enhanced_prompt
    
    def to_dict(self) -> Dict:
        """轉換為字典（僅用於記憶，不保存檔案）"""
        return {
            "character_name": self.character_name,
            "stories": self.stories,
            "personal_events": [{"event": e["event"].to_dict(), "added_at": e["added_at"]} 
                              for e in self.personal_events],
            "character_arc": self.character_arc,
            "secrets": self.secrets,
            "motivations": self.motivations
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """從字典創建"""
        background = cls(data["character_name"])
        background.stories = data.get("stories", [])
        background.character_arc = data.get("character_arc", [])
        background.secrets = data.get("secrets", [])
        background.motivations = data.get("motivations", [])
        
        # 還原事件
        personal_events = data.get("personal_events", [])
        for event_data in personal_events:
            event_dict = event_data["event"]
            event = StoryEvent(**event_dict)
            background.personal_events.append({
                "event": event,
                "added_at": event_data["added_at"]
            })
        
        return background

class CharacterBindingSystem:
    """角色綁定系統（記憶中，無檔案儲存）"""
    
    def __init__(self):
        self.character_backgrounds = {}  # {character_name: CharacterBackground}
        print("✅ 角色綁定系統初始化完成（記憶中）")
    
    def bind_background_to_character(self, character_name: str, background_data: Dict) -> str:
        """綁定背景故事到角色（僅記憶中）"""
        if character_name not in self.character_backgrounds:
            self.character_backgrounds[character_name] = CharacterBackground(character_name)
        
        story_id = self.character_backgrounds[character_name].add_story(
            background_data.get("title", "未命名背景"),
            background_data.get("content", ""),
            background_data.get("id")
        )
        
        print(f"✅ 背景故事綁定完成（記憶中）: {character_name} -> {background_data.get('title', '未命名')}")
        return story_id
    
    def bind_event_to_character(self, character_name: str, event: StoryEvent) -> bool:
        """綁定事件到角色（僅記憶中）"""
        if character_name not in self.character_backgrounds:
            self.character_backgrounds[character_name] = CharacterBackground(character_name)
        
        self.character_backgrounds[character_name].add_event(event)
        print(f"✅ 事件綁定完成（記憶中）: {character_name} -> {event.title}")
        return True
    
    def add_character_development(self, character_name: str, development: str) -> bool:
        """添加角色發展（僅記憶中）"""
        if character_name not in self.character_backgrounds:
            self.character_backgrounds[character_name] = CharacterBackground(character_name)
        
        self.character_backgrounds[character_name].add_to_character_arc(development)
        print(f"✅ 角色發展記錄完成（記憶中）: {character_name}")
        return True
    
    def clear_all_backgrounds(self) -> Dict[str, int]:
        """清除所有角色的背景資料"""
        results = {
            "characters_cleared": 0,
            "stories_cleared": 0,
            "events_cleared": 0,
            "arc_cleared": 0
        }
        
        for character_name, background in self.character_backgrounds.items():
            cleared_data = background.clear_all_background_data()
            results["characters_cleared"] += 1
            results["stories_cleared"] += cleared_data["stories_cleared"]
            results["events_cleared"] += cleared_data["events_cleared"]
            results["arc_cleared"] += cleared_data["arc_cleared"]
            print(f"✅ 清除角色背景資料: {character_name}")
        
        return results
    
    def clear_character_background(self, character_name: str) -> Dict[str, int]:
        """清除特定角色的背景資料"""
        if character_name in self.character_backgrounds:
            cleared_data = self.character_backgrounds[character_name].clear_all_background_data()
            print(f"✅ 清除角色背景資料: {character_name}")
            return {
                "character_cleared": character_name,
                **cleared_data
            }
        return {
            "character_cleared": character_name,
            "stories_cleared": 0,
            "events_cleared": 0,
            "arc_cleared": 0
        }
    
    def get_character_background(self, character_name: str) -> Optional[CharacterBackground]:
        """獲取角色背景（從記憶中）"""
        return self.character_backgrounds.get(character_name)
    
    def get_characters_with_backgrounds(self) -> List[str]:
        """獲取有背景故事的角色列表"""
        return list(self.character_backgrounds.keys())
    
    def remove_background_from_character(self, character_name: str, story_id: str) -> bool:
        """從角色移除背景故事"""
        if character_name in self.character_backgrounds:
            backgrounds = self.character_backgrounds[character_name]
            # 找到並移除指定ID的故事
            for i, story in enumerate(backgrounds.stories):
                if story["id"] == story_id:
                    backgrounds.stories.pop(i)
                    print(f"✅ 移除背景故事: {character_name} -> {story_id}")
                    return True
        return False
    
    def get_enhanced_prompt_for_character(self, character_name: str) -> str:
        """獲取角色的增強提示詞"""
        background = self.get_character_background(character_name)
        if background:
            return background.get_enhanced_prompt()
        return ""

class VirtualSandboxSociety:
    """模擬系統 - 完整自定義版本"""
    
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.customization = CustomizationManager()
        self.binding_system = CharacterBindingSystem()
        
        # 合併預設和自定義角色
        self.characters = self._merge_characters()
        
        # 合併預設和自定義場景
        self.scenes = self._merge_scenes()
        
        # 當前場景
        self.current_scene = self.scenes.get("虛擬對話空間", 
            SceneSetting(name="虛擬對話空間", location="虛擬空間", atmosphere="中性", time_period="現代"))
        
        self.conversation_history = []
        self.active_events = {}
    
    def _merge_characters(self) -> Dict[str, CharacterTrait]:
        """合併預設和自定義角色"""
        characters = {}
        
        # 預設角色
        default_characters = {
            "secretary": CharacterTrait(
                name="林秘書",
                personality="專業、細心、高效、有條理",
                values=["守時", "責任感", "忠誠", "保密"],
                speech_style="正式、禮貌、簡潔",
                background="畢業於頂尖商學院，有5年高管秘書經驗",
                profession="高級行政秘書",
                interests=["時間管理", "商務禮儀", "文書處理"],
                age=28,
                gender="女"
            ),
            "executive": CharacterTrait(
                name="王總監",
                personality="果斷、戰略性、結果導向、領導力強",
                values=["效率", "創新", "利潤", "團隊合作"],
                speech_style="直接、有力、數據驅動",
                background="從基層做起，15年管理經驗，帶領過百人團隊",
                profession="企業高管",
                interests=["市場分析", "策略規劃", "談判技巧"],
                age=42,
                gender="男"
            ),
            "mentor": CharacterTrait(
                name="小美",
                personality="有好感、注重自身想法、渴望被承認、易怒",
                values=["成長", "陪伴", "互動", "不理解"],
                speech_style="思考性、情緒化性、衝突性",
                background="剛出社會的英語老師，很缺乏安全感，渴望獲得主導地位，半年前認識，都是棒球愛好者",
                profession="女友",
                interests=["逛街", "追劇", "唱歌"],
                age=24,
                gender="女"
            )
        }
        
        # 添加預設角色
        for key, character in default_characters.items():
            characters[key] = character
        
        # 添加自定義角色
        custom_chars = self.customization.get_all_custom_characters()
        for name, character in custom_chars.items():
            characters[f"custom_{name}"] = character
        
        return characters
    
    def _merge_scenes(self) -> Dict[str, SceneSetting]:
        """合併預設和自定義場景"""
        scenes = {}
        
        # 預設場景
        default_scenes = {
            "辦公室": SceneSetting(
                name="辦公室",
                location="現代辦公室",
                atmosphere="專業、忙碌",
                time_period="工作日",
                description="整潔的辦公室環境，充滿工作的氛圍"
            ),
            "咖啡廳": SceneSetting(
                name="咖啡廳",
                location="城市咖啡廳",
                atmosphere="輕鬆、舒適",
                time_period="午後",
                description="溫馨的咖啡廳，飄散著咖啡香氣"
            ),
            "公園": SceneSetting(
                name="公園",
                location="城市公園",
                atmosphere="寧靜、自然",
                time_period="週末",
                description="綠意盎然的公園，讓人放鬆心情"
            ),
            "虛擬對話空間": SceneSetting(
                name="虛擬對話空間",
                location="虛擬空間",
                atmosphere="未來感、科技",
                time_period="現代",
                description="數位化的對話空間，充滿科技感"
            )
        }
        
        # 添加預設場景
        for name, scene in default_scenes.items():
            scenes[name] = scene
        
        # 添加自定義場景
        custom_scenes = self.customization.get_all_custom_scenes()
        for name, scene in custom_scenes.items():
            scenes[name] = scene
        
        return scenes
    
    def setup_scene(self, scene_name: str = None):
        """設定場景"""

        if scene_name in self.scenes:
            self.current_scene = self.scenes[scene_name]
            return (f"✅ 場景已設定: {scene_name}")
        else:
            return ("✅ 使用當前場景設定")
    
    def get_current_scene_info(self) -> Dict:
        """獲取當前場景資訊"""
        return {
            "name": self.current_scene.name,
            "location": self.current_scene.location,
            "atmosphere": self.current_scene.atmosphere,
            "time_period": self.current_scene.time_period,
            "description": self.current_scene.description
        }
    
    def initialize_system(self, reset_type: str = "soft") -> Dict[str, any]:
        """
        初始化系統，恢復到初始狀態
        
        Args:
            reset_type: "soft" - 僅清除記憶中的資料
                       "hard" - 清除所有自定義內容
                       "full" - 完全重置，包含預設角色
        """
        results = {
            "reset_type": reset_type,
            "success": True,
            "details": {}
        }
        
        try:
            if reset_type == "soft":
                # 軟重置：僅清除記憶中的資料
                results["details"]["conversation_history"] = len(self.conversation_history)
                self.conversation_history.clear()
                
                results["details"]["active_events"] = len(self.active_events)
                self.active_events.clear()
                
                # 清除綁定系統的記憶
                bg_results = self.binding_system.clear_all_backgrounds()
                results["details"]["backgrounds"] = bg_results
                
                print("✅ 軟重置完成：清除對話歷史和記憶中的背景資料")
                
            elif reset_type == "hard":
                # 硬重置：清除所有自定義內容
                results["details"]["soft_reset"] = {
                    "conversation_history": len(self.conversation_history),
                    "active_events": len(self.active_events)
                }
                self.conversation_history.clear()
                self.active_events.clear()
                
                # 清除綁定系統
                bg_results = self.binding_system.clear_all_backgrounds()
                results["details"]["backgrounds"] = bg_results
                
                # 清除所有自定義內容檔案
                custom_results = self.customization.clear_all_custom_content()
                results["details"]["custom_content"] = custom_results
                
                # 重新載入預設角色和場景
                self.characters = self._merge_characters()
                self.scenes = self._merge_scenes()
                
                print("✅ 硬重置完成：清除所有自定義內容")
                
            elif reset_type == "full":
                # 完全重置：包含刪除整個 custom 目錄
                results["details"]["soft_reset"] = {
                    "conversation_history": len(self.conversation_history),
                    "active_events": len(self.active_events)
                }
                self.conversation_history.clear()
                self.active_events.clear()
                
                # 清除綁定系統
                bg_results = self.binding_system.clear_all_backgrounds()
                results["details"]["backgrounds"] = bg_results
                
                # 刪除整個 custom 目錄
                if os.path.exists('custom'):
                    shutil.rmtree('custom')
                    results["details"]["custom_directory"] = "已刪除"
                    print("✅ 刪除 custom 目錄")
                
                # 重新創建目錄
                self.customization._ensure_directories()
                
                # 重新建立預設角色和場景
                default_characters = {
                    "secretary": CharacterTrait(
                        name="林秘書",
                        personality="專業、細心、高效、有條理",
                        values=["守時", "責任感", "忠誠", "保密"],
                        speech_style="正式、禮貌、簡潔",
                        background="畢業於頂尖商學院，有5年高管秘書經驗",
                        profession="高級行政秘書",
                        interests=["時間管理", "商務禮儀", "文書處理"],
                        age=28,
                        gender="女"
                    ),
                    "executive": CharacterTrait(
                        name="王總監",
                        personality="果斷、戰略性、結果導向、領導力強",
                        values=["效率", "創新", "利潤", "團隊合作"],
                        speech_style="直接、有力、數據驅動",
                        background="從基層做起，15年管理經驗，帶領過百人團隊",
                        profession="企業高管",
                        interests=["市場分析", "策略規劃", "談判技巧"],
                        age=42,
                        gender="男"
                    ),
                    "mentor": CharacterTrait(
                        name="小美",
                        personality="有好感、注重自身想法、渴望被承認、易怒",
                        values=["成長", "陪伴", "互動", "不理解"],
                        speech_style="思考性、情緒化性、衝突性",
                        background="剛出社會的英語老師，很缺乏安全感，渴望獲得主導地位，半年前認識，都是棒球愛好者",
                        profession="女友",
                        interests=["逛街", "追劇", "唱歌"],
                        age=24,
                        gender="女"
                    )
                }
                
                default_scenes = {
                    "辦公室": SceneSetting(
                        name="辦公室",
                        location="現代辦公室",
                        atmosphere="專業、忙碌",
                        time_period="工作日",
                        description="整潔的辦公室環境，充滿工作的氛圍"
                    ),
                    "咖啡廳": SceneSetting(
                        name="咖啡廳",
                        location="城市咖啡廳",
                        atmosphere="輕鬆、舒適",
                        time_period="午後",
                        description="溫馨的咖啡廳，飄散著咖啡香氣"
                    ),
                    "公園": SceneSetting(
                        name="公園",
                        location="城市公園",
                        atmosphere="寧靜、自然",
                        time_period="週末",
                        description="綠意盎然的公園，讓人放鬆心情"
                    ),
                    "虛擬對話空間": SceneSetting(
                        name="虛擬對話空間",
                        location="虛擬空間",
                        atmosphere="未來感、科技",
                        time_period="現代",
                        description="數位化的對話空間，充滿科技感"
                    )
                }
                
                # 重置角色和場景
                self.characters = default_characters
                self.scenes = default_scenes
                self.current_scene = self.scenes["虛擬對話空間"]
                
                # 重置自定義管理器
                self.customization = CustomizationManager()
                
                print("✅ 完全重置完成：系統恢復到出廠狀態")
            else:
                results["success"] = False
                results["error"] = f"不支援的重置類型: {reset_type}"
                return results
            
            # 設置默認場景
            self.current_scene = self.scenes.get("虛擬對話空間", 
                SceneSetting(name="虛擬對話空間", location="虛擬空間", atmosphere="中性", time_period="現代"))
            
            results["message"] = f"系統已成功初始化 ({reset_type}重置)"
            return results
            
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            return results
    
    def generate_role_response(self, role_key: str, user_input: str) -> str:
        """生成角色回應（整合增強提示詞）"""
        if role_key not in self.characters:
            return "抱歉，我不認識這個角色。"
        
        character = self.characters[role_key]
        
        # 構建完整的系統提示（包含綁定的背景故事）
        system_prompt = self._build_enhanced_system_prompt(character)
        
        # 格式化對話歷史
        history_text = self._format_conversation_history()
        
        # 完整提示
        full_prompt = f"""{system_prompt}

{history_text}

對話場景已轉移到: {self.current_scene.to_prompt()}

用戶說: {user_input}

請以{character.profession}的身份回應，保持角色一致性:"""
        
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": full_prompt},
                    {"role": "user", "content": user_input}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.7,
                max_tokens=300
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # 記錄對話
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": dt.datetime.now().isoformat(),
                "character": character.name,
                "scene": self.current_scene.name
            })
            
            self.conversation_history.append({
                "role": "character",
                "content": response_text,
                "timestamp": dt.datetime.now().isoformat(),
                "character": character.name,
                "scene": self.current_scene.name
            })
            
            # 限制歷史長度
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return response_text
            
        except Exception as e:
            print(f"❌ 生成回應失敗: {e}")
            return f"抱歉，我暫時無法回應。請稍後再試。"
    
    def _build_enhanced_system_prompt(self, character: CharacterTrait) -> str:
        """構建增強系統提示（包含綁定的背景故事）"""
        # 基本角色提示
        base_prompt = f"""你是一個專業的虛擬沙盒社會角色扮演AI。你現在正在扮演以下角色：

{character.to_prompt()}"""

        # 添加綁定的背景故事
        enhanced_background = self.binding_system.get_enhanced_prompt_for_character(character.name)
        if enhanced_background:
            base_prompt += enhanced_background
        
        # 角色扮演要求
        base_prompt += f"""

角色扮演要求:
1. 嚴格保持角色的一致性
2. 根據角色的性格、價值觀和背景回應
3. 使用符合角色身份的說話風格
4. 可以適當展現角色的專業知識和興趣
5. 回應要自然、有深度，展現角色的思考過程
6. 可以提出問題、給予建議或分享見解

記住：你不是AI助手，你就是{character.profession}！"""
        
        return base_prompt
    
    def _format_conversation_history(self) -> str:
        """格式化對話歷史"""
        if not self.conversation_history:
            return "這是對話的開始。"
        
        history_text = "之前的對話:\n"
        for entry in self.conversation_history[-5:]:
            role = "用戶" if entry["role"] == "user" else "角色"
            history_text += f"{role}: {entry['content']}\n"
        
        return history_text
    
    # 自定義管理方法
    def create_custom_character(self, **kwargs) -> CharacterTrait:
        """創建自定義角色"""
        try:
            character = CharacterTrait(**kwargs)
            success = self.customization.save_custom_character(character)
            if success:
                # 更新當前角色列表
                self.characters[f"custom_{character.name}"] = character
            return character
        except Exception as e:
            print(f"❌ 創建角色失敗: {e}")
            return None
    
    def create_custom_scene(self, **kwargs) -> SceneSetting:
        """創建自定義場景"""
        try:
            scene = SceneSetting(**kwargs)
            success = self.customization.save_custom_scene(scene)
            if success:
                # 更新當前場景列表
                self.scenes[scene.name] = scene
            return scene
        except Exception as e:
            print(f"❌ 創建場景失敗: {e}")
            return None
    
    def create_custom_background(self, title: str, content: str, character_name: str = "") -> Dict:
        """創建自定義背景故事（僅記憶中）"""
        try:
            background = {
                "id": str(uuid.uuid4())[:8],
                "title": title,
                "content": content,
                "character_name": character_name,
                "created_at": dt.datetime.now().isoformat()
            }
            # 直接添加到記憶中，不保存檔案
            self.customization.add_custom_background(background)
            return background
        except Exception as e:
            print(f"❌ 創建背景失敗: {e}")
            return None
    
    def get_all_characters(self) -> Dict[str, CharacterTrait]:
        """獲取所有角色（包含自定義）"""
        return self.characters
    
    def get_all_scenes(self) -> Dict[str, SceneSetting]:
        """獲取所有場景（包含自定義）"""
        return self.scenes
    
    def get_all_backgrounds(self) -> Dict[str, Dict]:
        """獲取所有背景故事（從記憶中）"""
        return self.customization.get_all_custom_backgrounds()
    
    def delete_custom_character(self, character_name: str) -> bool:
        """刪除自定義角色"""
        success = self.customization.delete_custom_character(character_name)
        if success:
            # 從當前列表移除
            custom_key = f"custom_{character_name}"
            if custom_key in self.characters:
                del self.characters[custom_key]
        return success
    
    def delete_custom_scene(self, scene_name: str) -> bool:
        """刪除自定義場景"""
        success = self.customization.delete_custom_scene(scene_name)
        if success:
            # 從當前列表移除
            if scene_name in self.scenes:
                del self.scenes[scene_name]
        return success
    
    def bind_background_to_character(self, character_name: str, background_data: Dict) -> str:
        """綁定背景故事到角色（僅記憶中）"""
        return self.binding_system.bind_background_to_character(character_name, background_data)
    
    def bind_event_to_character(self, character_name: str, event_data: Dict) -> bool:
        """綁定事件到角色（僅記憶中）"""
        try:
            event = StoryEvent(**event_data)
            return self.binding_system.bind_event_to_character(character_name, event)
        except Exception as e:
            print(f"❌ 綁定事件失敗: {e}")
            return False
    
    def get_character_background_info(self, character_name: str) -> Optional[str]:
        """獲取角色背景資訊"""
        background = self.binding_system.get_character_background(character_name)
        if background:
            return background.get_background_summary()
        return None
    
    def get_character_with_backgrounds(self) -> List[Dict]:
        """獲取有背景故事的角色列表"""
        characters_with_bg = []
        for char_name in self.binding_system.get_characters_with_backgrounds():
            # 找到對應的角色對象
            for key, char in self.characters.items():
                if char.name == char_name:
                    characters_with_bg.append({
                        "character": char,
                        "key": key,
                        "background_count": len(self.binding_system.character_backgrounds[char_name].stories),
                        "event_count": len(self.binding_system.character_backgrounds[char_name].personal_events)
                    })
                    break
        return characters_with_bg
    
    def _is_event_suitable_for_character(self, event: StoryEvent, character_name: str, background: CharacterBackground) -> bool:
        """判斷事件是否適合角色"""
        # 檢查事件是否已經綁定
        for personal_event in background.personal_events:
            if personal_event["event"].id == event.id:
                return False
        
        # 檢查角色是否在涉及角色列表中
        if character_name in event.involved_characters:
            return True
        
        # 根據事件類型進行判斷
        if event.event_type == "personal" and "個人" in event.description:
            return True
        
        return False
    
    def get_enhanced_character_prompt(self, character_key: str) -> str:
        """獲取增強的角色提示（包含背景故事）"""
        if character_key not in self.characters:
            return ""
        
        character = self.characters[character_key]
        basic_prompt = character.to_prompt()
        
        # 添加背景故事
        background = self.binding_system.get_character_background(character.name)
        if background and background.stories:
            background_text = "\n📖 角色背景故事:\n"
            for story in background.stories[-2:]:  # 最近2個背景故事
                background_text += f"• {story['title']}: {story['content']}\n"
            
            basic_prompt += background_text
        
        # 添加角色發展
        if background and background.character_arc:
            development_text = "\n📈 角色發展歷程:\n"
            for arc in background.character_arc[-3:]:  # 最近3個發展
                development_text += f"• {arc['development']}\n"
            
            basic_prompt += development_text
        
        return basic_prompt
    
    def update_conversation_with_background(self, character_key: str, user_input: str, response: str):
        """更新對話並記錄角色發展"""
        character = self.characters.get(character_key)
        if not character:
            return
        
        # 記錄對話
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": dt.datetime.now().isoformat(),
            "character": character.name,
            "scene": self.current_scene.name
        })
        
        self.conversation_history.append({
            "role": "character",
            "content": response,
            "timestamp": dt.datetime.now().isoformat(),
            "character": character.name,
            "scene": self.current_scene.name
        })
        
        # 限制歷史長度
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
        
        # 檢查是否需要記錄角色發展（深層次對話）
        if len(user_input) > 50 and len(response) > 50:
            development = f"與用戶進行了深層次對話: {user_input[:30]}..."
            self.binding_system.add_character_development(character.name, development)

# 測試
if __name__ == "__main__":
    print("🧪 測試初始化系統功能...")
    
    # 模擬Groq客戶端
    class MockGroqClient:
        class chat:
            class completions:
                @staticmethod
                def create(messages, model, temperature, max_tokens):
                    class MockResponse:
                        class Choice:
                            class Message:
                                content = "這是一個模擬回應。"
                            message = Message()
                        choices = [Choice()]
                    return MockResponse()
    
    groq_client = MockGroqClient()
    society = VirtualSandboxSociety(groq_client)
    
    # 測試初始化系統
    print("\n1. 測試軟重置...")
    soft_result = society.initialize_system("soft")
    print(f"軟重置結果: {soft_result}")
    
    # 創建一些測試數據
    print("\n2. 創建測試數據...")
    society.create_custom_background(
        title="測試背景",
        content="這是一個測試背景故事",
        character_name="王總監"
    )
    
    society.create_custom_character(
        name="測試角色",
        personality="測試性格",
        values=["測試價值"],
        speech_style="測試風格",
        background="測試背景",
        profession="測試職業",
        interests=["測試興趣"],
        age=30,
        gender="男"
    )
    
    # 添加對話歷史
    society.conversation_history.append({
        "role": "user",
        "content": "測試對話",
        "timestamp": dt.datetime.now().isoformat(),
        "character": "王總監",
        "scene": "辦公室"
    })
    
    print(f"對話歷史長度: {len(society.conversation_history)}")
    print(f"自定義角色數量: {len([c for c in society.characters.keys() if 'custom_' in c])}")
    
    print("\n3. 測試硬重置...")
    hard_result = society.initialize_system("hard")
    print(f"硬重置結果: {hard_result}")
    
    print(f"重置後對話歷史長度: {len(society.conversation_history)}")
    print(f"重置後自定義角色數量: {len([c for c in society.characters.keys() if 'custom_' in c])}")
    
    print("\n✅ 初始化系統功能測試完成")