import os

from models.utils import clean_prompt, safe_read_json, safe_write_json


MEM_PATH = os.path.join("data", "memory.json")
MAX_EXPERIENCES = 600
MAX_VALUE_CHARS = 500


class MemoryManager:
    @staticmethod
    def load() -> dict:
        os.makedirs("data", exist_ok=True)
        data = safe_read_json(MEM_PATH)
        return data if isinstance(data, dict) else {}

    @staticmethod
    def save(mem: dict) -> None:
        safe_write_json(MEM_PATH, mem)

    @staticmethod
    def add_experience(key: str, value: str) -> None:
        key = clean_prompt(key, max_chars=120)
        value = clean_prompt(value, max_chars=MAX_VALUE_CHARS)
        if not key or not value:
            return

        mem = MemoryManager.load()
        experiences = mem.setdefault("experiences", [])
        if not isinstance(experiences, list):
            experiences = []

        item = {"key": key, "val": value}
        if item not in experiences:
            experiences.append(item)

        mem["experiences"] = experiences[-MAX_EXPERIENCES:]
        MemoryManager.save(mem)

    @staticmethod
    def list_experiences() -> list[dict]:
        experiences = MemoryManager.load().get("experiences", [])
        return experiences if isinstance(experiences, list) else []

    @staticmethod
    def compact_and_filter() -> None:
        seen = set()
        compacted = []
        for item in MemoryManager.list_experiences():
            key = str(item.get("key", ""))
            value = str(item.get("val", ""))
            pair = (key, value)
            if key and value and pair not in seen:
                seen.add(pair)
                compacted.append({"key": key[:120], "val": value[:MAX_VALUE_CHARS]})

        MemoryManager.save({"experiences": compacted[-MAX_EXPERIENCES:]})

    @staticmethod
    def get_user_memory_str(user_id: str) -> str:
        target_key = f"User_{user_id}"
        found: list[str] = []

        for item in MemoryManager.list_experiences():
            key = str(item.get("key", ""))
            value = str(item.get("val", ""))
            if target_key in key:
                simple_key = key.replace(target_key + "_", "")
                found.append(f"- {simple_key}: {value[:MAX_VALUE_CHARS]}")

        if not found:
            return "目前沒有可靠的長期記憶。"
        return "\n".join(found[:30])
