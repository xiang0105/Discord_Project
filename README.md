# discord_project

一個以 Discord 為介面、使用 Google Gemini 產生回覆的聊天 Bot。

此專案支援：
- 一般訊息自動回覆（`on_message`）
- Slash Command（`/chat`、`/reset`、`/force_evolve`）
- 對話歷史儲存（`data/history.json`）
- 使用者記憶萃取與累積（`data/memory.json`）
- Bot 經歷演化（寫回 `data/config.json` 的 `generated_experiences`）

## 功能總覽

- 人設與語氣設定：從 `data/config.json` 讀取 `base_setting`、`interests`、`speaking_style`。
- 頻道白名單：`allowed_channels` 可限制 Bot 僅在指定頻道回應。
  - 若為空陣列 `[]`，代表所有頻道都會回應。
- 歷史記錄：每位使用者以 user id 分組儲存在 `data/history.json`。
- 記憶機制：演化任務會將偏好與特質寫入 `data/memory.json`。
- 自動演化：使用者一段時間未互動後，背景任務會整理對話並更新記憶。

## 專案結構

```text
.
├─ main.py
├─ requirements.txt
├─ data/
│  ├─ config.example.json
│  ├─ config.json
│  ├─ history.json
│  └─ memory.json
└─ models/
   ├─ ai_model.py
   ├─ config_manager.py
   ├─ evolution_task.py
   ├─ history_manager.py
   ├─ memory_manager.py
   ├─ message_handler.py
   ├─ sticker_manager.py
   └─ utils.py
```

## 執行需求

- Python 3.10+
- 一個 Discord Bot Token
- Google AI API Key（Gemini）

## 安裝與啟動

### 1. 建立虛擬環境（建議）

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. 安裝依賴

```powershell
pip install -r requirements.txt
```

### 3. 設定環境變數

複製範本：

```powershell
Copy-Item .env.example .env
```

編輯 `.env`：

```env
DISCORD_TOKEN=your_discord_bot_token
GOOGLE_API_KEY=your_google_api_key
BOT_OWNER_ID=your_discord_user_id
```

### 4. 設定 Bot 行為

若你要自訂人設，先建立設定檔：

```powershell
Copy-Item data\config.example.json data\config.json
```

然後編輯 `data/config.json`，例如：

- `base_setting.name`
- `base_setting.role`
- `base_setting.background`
- `interests`
- `speaking_style`
- `allowed_channels`

> 注意：`main.py` 會在啟動時檢查 `DISCORD_TOKEN` 與 `GOOGLE_API_KEY`。缺少任一值會直接結束。

### 5. 啟動

```powershell
python main.py
```

若啟動成功，終端機會看到類似訊息：

- `xxx 已上線，/chat 可用`
- `[System] 背景演化任務已啟動 (每 30 秒檢查一次)`

## Discord 端必要設定

在 Discord Developer Portal 建議至少確認：

- Privileged Gateway Intents:
  - `MESSAGE CONTENT INTENT` 開啟
- OAuth2 Scopes:
  - `bot`
  - `applications.commands`
- Bot Permissions（至少）：
  - `View Channels`
  - `Send Messages`
  - `Read Message History`
  - `Use Application Commands`

## 指令說明

- `/chat <user_message>`
  - 帶入歷史對話呼叫模型，回覆內容。
- `/reset`
  - 清除該使用者在 `history.json` 的歷史。
- `/force_evolve`
  - 強制讀取該使用者歷史並分批演化，更新記憶。

此外，Bot 也會直接回覆一般文字訊息（`on_message`）。

## 資料檔案說明

- `data/config.json`
  - 非敏感設定（人設、白名單、Bot 經歷）。
- `data/history.json`
  - 對話歷史（依 user id 儲存）。
- `data/memory.json`
  - 演化後的記憶片段。

`.gitignore` 已排除上述敏感與本機資料，不會預設提交：

- `.env`
- `data/config.json`
- `data/history.json`
- `data/memory.json`

## 常見問題

- 啟動時顯示「請在環境變數或 .env 設定 GOOGLE_API_KEY」
  - 檢查 `.env` 是否存在、名稱是否正確、值是否有效。
- Bot 上線但沒有回覆
  - 檢查是否開啟 Message Content Intent。
  - 檢查 `allowed_channels` 是否限制到其他頻道。
- `/chat` 看不到
  - 確認邀請連結包含 `applications.commands` scope。
  - 重新邀請 Bot 或等待指令同步完成。

## 備註

- 目前模型在 `models/ai_model.py` 內固定為 `gemini-2.0-flash-lite`。
- 若要調整演化節奏，可修改 `models/evolution_task.py` 中的檢查與閒置秒數。