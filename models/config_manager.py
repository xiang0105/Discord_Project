# config_manager.py
# 提供載入/儲存 config，並提供簡單的 getter

import json
import os
from typing import Dict

CONFIG_PATH = os.path.join('data', 'config.json')

class ConfigManager:
    @staticmethod
    def load() -> Dict:
        if not os.path.exists('data'):
            os.makedirs('data')

        # 預設值
        default = {
        'bot_owner_id': '',
        'allowed_channels': [],
        'base_setting': {
            'name': 'PhiLia',
            'role': '助手',
            'background': '無'
        },
        'interests': [],
        'speaking_style': [],
        'generated_experiences': []
        }

        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                loaded = json.load(f)

            # Keep non-sensitive settings in config.json only.
            sanitized = {
                k: v for k, v in loaded.items()
                if k not in ('google_api_key', 'discord_token')
            }
            config = {**default, **sanitized}

            # Auto-migrate old config files that still contain secrets.
            if ('google_api_key' in loaded) or ('discord_token' in loaded):
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
            return config
        
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default

    @staticmethod
    def save(config: Dict):
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)