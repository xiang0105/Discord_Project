# history_manager.py
# 簡單的歷史紀錄/讀寫（針對每個 user 存 json）

import json
import os
from typing import List

HISTORY_FILE = os.path.join('data', 'history.json')

class HistoryManager:
    @staticmethod
    def load_all() -> dict:
        if not os.path.exists('data'):
            os.makedirs('data')
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return {}
        return {}

    @staticmethod
    def save_all(data: dict):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def append_message(user_id: str, role: str, content: str):
        all_hist = HistoryManager.load_all()
        user_hist = all_hist.get(user_id, [])
        user_hist.append({'role': role, 'parts': [content]})
        all_hist[user_id] = user_hist
        HistoryManager.save_all(all_hist)

    @staticmethod
    def get_user_history(user_id: str) -> List[dict]:
        return HistoryManager.load_all().get(user_id, [])

    @staticmethod
    def clear_user(user_id: str):
        all_hist = HistoryManager.load_all()
        if user_id in all_hist:
            del all_hist[user_id]
            HistoryManager.save_all(all_hist)