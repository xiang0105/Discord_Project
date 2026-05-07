import os

from models.utils import clean_prompt, safe_read_json, safe_write_json


HISTORY_FILE = os.path.join("data", "history.json")
DEFAULT_MAX_MESSAGES = 40
MAX_MESSAGE_CHARS = 4000


class HistoryManager:
    @staticmethod
    def load_all() -> dict:
        os.makedirs("data", exist_ok=True)
        data = safe_read_json(HISTORY_FILE)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def save_all(data: dict) -> None:
        safe_write_json(HISTORY_FILE, data)

    @staticmethod
    def append_message(
        user_id: str,
        role: str,
        content: str,
        *,
        max_messages: int = DEFAULT_MAX_MESSAGES,
    ) -> None:
        if role not in {"user", "model"}:
            raise ValueError("role must be 'user' or 'model'")

        all_hist = HistoryManager.load_all()
        user_hist = all_hist.get(user_id, [])
        if not isinstance(user_hist, list):
            user_hist = []

        user_hist.append(
            {
                "role": role,
                "parts": [clean_prompt(content, max_chars=MAX_MESSAGE_CHARS)],
            }
        )
        all_hist[user_id] = user_hist[-max_messages:]
        HistoryManager.save_all(all_hist)

    @staticmethod
    def get_user_history(user_id: str, *, max_messages: int = DEFAULT_MAX_MESSAGES) -> list[dict]:
        history = HistoryManager.load_all().get(user_id, [])
        if not isinstance(history, list):
            return []
        return history[-max_messages:]

    @staticmethod
    def clear_user(user_id: str) -> None:
        all_hist = HistoryManager.load_all()
        if user_id in all_hist:
            del all_hist[user_id]
            HistoryManager.save_all(all_hist)
