# discord_project

一個使用 Discord.py 與 Google Gemini 的 Discord 聊天 bot。

## 功能

- 一般頻道訊息回覆，可用 `respond_to_all_messages` 關閉
- Slash commands：`/chat`、`/reset`、`/force_evolve`
- 每位使用者的聊天歷史保存在 `data/history.json`
- 長期記憶保存在 `data/memory.json`
- Bot 角色與回覆風格設定保存在 `data/config.json`

## 資安重點

- `DISCORD_TOKEN`、`GOOGLE_API_KEY`、`BOT_OWNER_ID` 必須放在 `.env`，不要放進 `config.json`
- `ConfigManager` 會自動移除舊設定檔中的常見敏感 key
- 使用者輸入會限制長度並遮罩常見 token/API key
- system prompt 加入反 prompt injection 規則，歷史與記憶都被視為不可信資料
- `/force_evolve` 只有 `BOT_OWNER_ID` 能使用
- 預設不會把被 mention 的其他使用者記憶放進 prompt，除非設定 `allow_mentioned_user_memory: true`
- history 與 memory 會限制保存數量與單筆長度

## 安裝

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
Copy-Item data\config.example.json data\config.json
```

編輯 `.env`：

```env
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_API_KEY=your_google_api_key
BOT_OWNER_ID=your_discord_user_id
```

`allowed_channels` 為空陣列時代表所有頻道都可使用。正式部署時建議填入指定頻道 ID。

## 啟動

```powershell
python main.py
```

Discord Developer Portal 需要啟用：

- OAuth2 scopes：`bot`、`applications.commands`
- Bot permissions：`View Channels`、`Send Messages`、`Read Message History`、`Use Application Commands`
- 若要讀取一般訊息，需啟用 `MESSAGE CONTENT INTENT`

## 指令

- `/chat <user_message>`：和 bot 聊天
- `/reset`：清除自己的聊天歷史
- `/force_evolve`：owner 手動整理自己的歷史成長期記憶

## 本機資料

`.gitignore` 已排除：

- `.env`
- `data/config.json`
- `data/history.json`
- `data/memory.json`
