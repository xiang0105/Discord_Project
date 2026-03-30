# evolution_task.py
# 背景任務：負責自動演化（呼叫 AI 做深度總結），並把結果回寫到 data/config.json & data/memory.json

import asyncio
import datetime
import re
from models.ai_model import AIModel
from models.config_manager import ConfigManager
from models.memory_manager import MemoryManager

class EvolutionTask:
    def __init__(self, bot, ai_model: AIModel, config: dict, message_handler):
        self.bot = bot
        self.ai_model = ai_model
        self.config = config
        self.message_handler = message_handler
        self._unsaved = {} # user_id -> conversation string
        self._last_interaction = {} # user_id -> datetime

    # def start(self):
    #     self._loop = asyncio.get_event_loop()
    #     self._task = self._loop.create_task(self._runner())
    #     print("[System] 背景演化任務已啟動 (每 30 秒檢查一次)")

    async def run(self):
        print("[System] 背景演化任務已啟動 (每 30 秒檢查一次)")
        while True:
            await asyncio.sleep(30)
            await self.check_all()

    async def _runner(self):
        while True:
            await asyncio.sleep(30)
            await self.check_all()

    async def check_all(self):
        print("[Debug] 正在檢查是否有需要演化的對話...") #這行怕太吵可以註解掉
        now = datetime.datetime.now()
        to_process = []
        for uid, last in list(self._last_interaction.items()):
            # 計算距離上次說話過了幾秒
            diff = (now - last).total_seconds()
            
            # 若暫存有東西，且超過 30 秒沒說話
            if self._unsaved.get(uid):
                if diff > 30:
                    print(f"[Debug] User {uid} 已安靜 {int(diff)} 秒，準備執行演化...")
                    to_process.append(uid)
                else:
                    print(f"[Debug] User {uid} 累積對話中... (安靜 {int(diff)}/30 秒)")

        for uid in to_process:
            conv = self._unsaved.get(uid, '')
            await self.run_evolution(uid, conv)
            # 清除已處理的暫存
            self._unsaved.pop(uid, None)
            self._last_interaction.pop(uid, None)

    def touch_user(self, user_id: str, conversation_fragment: str):
        # 被 message_handler 呼叫以推進記憶
        now = datetime.datetime.now()
        self._last_interaction[user_id] = now
        self._unsaved.setdefault(user_id, '')
        self._unsaved[user_id] += conversation_fragment + "\n"
        print(f"[Debug] 已捕捉 User {user_id} 對話片段 (目前累積長度: {len(self._unsaved[user_id])} 字)")

    async def run_evolution(self, user_id: str, conversation_text: str):                  
        print(f"[Debug] 開始為 User {user_id} 執行 AI 分析...")
        
        system = self.ai_model.build_system_instruction(self.config)
        prompt = f"""
        以下是與使用者（id={user_id}）的對話片段：
        {conversation_text}
        
        請你以第一人稱總結：
        1. 使用者是否提到了自己的「名字/稱呼」？
        2. 使用者是否提到了「對其他人的稱呼、關係或看法」（特別是有 @Mention 的對象）？
        3. 使用者的「興趣/偏好/重要事件/價值觀」？
        
        請用 JSON 回傳，格式：
        {{
            "summary": "短句", 
            "name": "使用者的名字", 
            "traits": ["..."], 
            "likes": ["..."], 
            "dislikes": ["..."],
            "social_relations": ["使用者說 @某某 是...", "使用者覺得 @某某 ..."] 
        }}
        只回傳純粹的 JSON，不要 Markdown，不要解釋。
        """
        try:
            model = self.ai_model.start_chat(system_instruction=system)
            resp = await model.generate_content_async(prompt)
            text = resp.text.strip()
            
            # 除錯：印出 AI 原始回覆，如果解析失敗，這行救命
            # print(f"[Debug] AI 回傳原始資料: {text[:50]}...") 

            # 清理 Markdown
            text = text.replace("```json", "").replace("```", "")
            
            # 嘗試解析 JSON
            import json
            data = None
            try:
                data = json.loads(text)
            except Exception as e:
                print(f"[Error] JSON 解析失敗！AI 回傳了非 JSON 格式：\n{text}")
                # 容錯：嘗試抓取大括號內容
                m = re.search(r"\{.*\}", text, re.S)
                if m:
                    try:
                        data = json.loads(m.group(0))
                        print("[Debug] 正規表達式救援成功！")
                    except:
                        pass
                    
            # 若成功解析，寫入 Memory
            if data:
                print(f"✅ 演化成功！解析 User {user_id} 資料: {data}")
                
                if data.get('name'):
                    MemoryManager.add_experience(f"User_{user_id}_Name", data['name'])

                # 寫入 MemoryManager
                categories_to_save = ['traits', 'likes', 'dislikes', 'important_events']
                
                if 'social_relations' in data and isinstance(data['social_relations'], list):
                    for rel in data['social_relations']:
                        MemoryManager.add_experience(f"User_{user_id}_Social", rel)
                
                for cat in categories_to_save:
                    if cat in data and isinstance(data[cat], list):
                        for item in data[cat]:
                            MemoryManager.add_experience(f"User_{user_id}_{cat}", item)

                # 寫入 ConfigManager (Bot 經歷)
                if 'summary' in data:
                    current_config = ConfigManager.load()
                    if 'generated_experiences' not in current_config:
                        current_config['generated_experiences'] = []
                    
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_experience = f"[{timestamp}] (User {user_id}) {data['summary']}"
                    current_config['generated_experiences'].append(new_experience)
                    
                    ConfigManager.save(current_config)
                    print(f"✅ 已新增 Bot 經歷: {new_experience}")
            else:
                print(f"[Warning] 雖然 AI 有回應，但無法提取有效資料。")

        except Exception as e:
            print(f"[Critical Error] 演化任務發生嚴重錯誤: {e}")