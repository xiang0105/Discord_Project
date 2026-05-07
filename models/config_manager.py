import os
from typing import Any

from models.utils import safe_read_json, safe_write_json


CONFIG_PATH = os.path.join("data", "config.json")
SECRET_KEYS = {"google_api_key", "discord_token", "token", "api_key"}


DEFAULT_CONFIG: dict[str, Any] = {
    "bot_owner_id": "",
    "allowed_channels": [],
    "respond_to_all_messages": True,
    "allow_mentioned_user_memory": False,
    "max_history_messages": 40,
    "base_setting": {
        "name": "PhiLia",
        "role": "陪伴型 Discord 助手",
        "background": "友善、可靠、重視使用者安全。",
    },
    "interests": [],
    "speaking_style": [],
    "generated_experiences": [],
    "examples": [],
}


class ConfigManager:
    @staticmethod
    def load() -> dict:
        os.makedirs("data", exist_ok=True)
        loaded = safe_read_json(CONFIG_PATH)

        if not isinstance(loaded, dict):
            safe_write_json(CONFIG_PATH, DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        sanitized = {k: v for k, v in loaded.items() if k.lower() not in SECRET_KEYS}
        config = {**DEFAULT_CONFIG, **sanitized}
        config["base_setting"] = {
            **DEFAULT_CONFIG["base_setting"],
            **config.get("base_setting", {}),
        }
        config["allowed_channels"] = ConfigManager._normalize_channel_ids(
            config.get("allowed_channels", [])
        )

        if sanitized != loaded:
            safe_write_json(CONFIG_PATH, config)
        return config

    @staticmethod
    def save(config: dict) -> None:
        sanitized = {k: v for k, v in config.items() if k.lower() not in SECRET_KEYS}
        safe_write_json(CONFIG_PATH, sanitized)

    @staticmethod
    def _normalize_channel_ids(value: Any) -> list[int]:
        if not isinstance(value, list):
            return []

        ids: list[int] = []
        for item in value:
            try:
                channel_id = int(item)
            except (TypeError, ValueError):
                continue
            if channel_id > 0:
                ids.append(channel_id)
        return ids
