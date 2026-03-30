# memory_manager.py
# 實作 B 方案：深度個性化記憶
# 儲存格式：data/memory.json

import json
import os
from typing import List, Dict

MEM_PATH = os.path.join('data', 'memory.json')

class MemoryManager:
    @staticmethod
    def load() -> Dict:
        if not os.path.exists('data'):
            os.makedirs('data')
        if os.path.exists(MEM_PATH):
            with open(MEM_PATH, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def save(mem: Dict):
        with open(MEM_PATH, 'w', encoding='utf-8') as f:
            json.dump(mem, f, ensure_ascii=False, indent=4)

    @staticmethod
    def add_experience(key: str, value: str):
        mem = MemoryManager.load()
        if 'experiences' not in mem:
            mem['experiences'] = []
        mem['experiences'].append({'key': key, 'val': value})
        MemoryManager.save(mem)

    @staticmethod
    def list_experiences() -> List[Dict]:
        return MemoryManager.load().get('experiences', [])

    @staticmethod
    def compact_and_filter():
        # 簡單去重與合併，這裡可以補強 NLP 處理
        mem = MemoryManager.load()
        ex = mem.get('experiences', [])
        seen = set()
        new = []
        for e in ex:
            tup = (e.get('key'), e.get('val'))
            if tup not in seen:
                seen.add(tup)
                new.append(e)
        mem['experiences'] = new
        MemoryManager.save(mem)
        
    @staticmethod
    def get_user_memory_str(user_id: str) -> str:
        """撈出該使用者的所有記憶，組合成一段字串"""
        mem = MemoryManager.load()
        ex = mem.get('experiences', [])
        
        found = []
        # 搜尋 key 裡面包含該 User ID 的紀錄
        # (因為我們在 evolution_task 存的時候是存 "User_{id}_xxx")
        target_key = f"User_{user_id}"
        
        for item in ex:
            k = item.get('key', '')
            v = item.get('val', '')
            if target_key in k:
                # 簡單格式化： "User_123_likes: 喜歡吃蘋果" -> "likes: 喜歡吃蘋果"
                simple_key = k.replace(target_key + "_", "") 
                found.append(f"- {simple_key}: {v}")
        
        if not found:
            return "（目前對此使用者尚無具體記憶）"
            
        return "\n".join(found)