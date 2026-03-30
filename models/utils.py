# utils.py
# 共用工具函式：切字串、safe json io、timestamp 等

import json
import os
import datetime
from typing import Any, Optional, List, Dict

def smart_split(text: str, limit: int = 1900) -> List[str]:
    """
    把長文字依照換行或長度切成多段，確保不會超過 limit。
    回傳一串片段（每段 <= limit）。
    """
    parts: List[str] = []
    if not text:
        return parts

    remaining = text
    while len(remaining) > limit:
        cut = remaining[:limit]
        last_n = cut.rfind("\n")
        if last_n == -1:
            # 找不到換行就硬切
            last_n = limit
        parts.append(remaining[:last_n])
        remaining = remaining[last_n:].lstrip("\n")
    if remaining:
        parts.append(remaining)
    return parts


# ---- safe json io helpers ----
def safe_read_json(path: str) -> Optional[Any]:
    """安全讀取 JSON 檔案，若不存在或 parse 失敗回傳 None"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def safe_write_json(path: str, data: Any) -> bool:
    """安全寫入 JSON（會建立目錄），成功回傳 True"""
    try:
        dirpath = os.path.dirname(path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print("safe_write_json failed:", e)
        return False

def timestamp_now() -> str:
    """回傳現在時間的 ISO 字串（本地 time）"""
    return datetime.datetime.now().isoformat(timespec='seconds')

def ensure_str(x: Any) -> str:
    """把任何東西轉成安全字串表示（避免 None）"""
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    try:
        return str(x)
    except Exception:
        return ""

# 其他常用工具可以放在這裡，例如：clean_prompt, truncate, normalize_whitespace
def clean_prompt(s: str) -> str:
    """簡單清理 prompt：去頭尾空白並壓縮連續空白到單一空白"""
    if not s:
        return ""
    return " ".join(s.strip().split())
