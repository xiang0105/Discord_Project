import datetime
import json
import os
import re
import tempfile
from typing import Any, Optional


SECRET_PATTERNS = [
    re.compile(r"(DISCORD_TOKEN|GOOGLE_API_KEY|BOT_TOKEN)\s*=\s*[^\s]+", re.I),
    re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
    re.compile(r"[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27,}"),
]


def smart_split(text: str, limit: int = 1900) -> list[str]:
    parts: list[str] = []
    if not text:
        return parts

    remaining = text
    while len(remaining) > limit:
        cut = remaining[:limit]
        last_newline = cut.rfind("\n")
        split_at = last_newline if last_newline > 200 else limit
        parts.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip("\n")

    if remaining:
        parts.append(remaining)
    return parts


def safe_read_json(path: str) -> Optional[Any]:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return None


def safe_write_json(path: str, data: Any) -> bool:
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory or None)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
        os.replace(tmp_path, path)
        return True
    except OSError:
        return False


def timestamp_now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def ensure_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def clean_prompt(text: str, *, max_chars: int = 4000) -> str:
    if not text:
        return ""
    text = remove_control_chars(text)
    return " ".join(text.strip().split())[:max_chars]


def remove_control_chars(text: str) -> str:
    return "".join(ch for ch in text if ch == "\n" or ch == "\t" or ord(ch) >= 32)


def redact_secrets(text: str) -> str:
    redacted = text
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def extract_json_object(text: str) -> dict | None:
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None
