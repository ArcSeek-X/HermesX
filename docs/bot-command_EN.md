# Bot Integration Guide

This document covers the bot module architecture, supported commands, webhook routes, and how to configure platform integrations.

> **Glossary:** "Enterprise bot" in this context means a chatbot that receives commands via webhook from a messaging platform (Feishu / DingTalk / WeChat Work / Telegram) and calls the analysis pipeline to reply inline.

---

## 1. Architecture Overview

```mermaid
flowchart TB
    subgraph Platforms [Messaging Platforms]
        FS[Feishu]
        DT[DingTalk]
        WC[WeChat Work]
        TG[Telegram]
        More[More platforms...]
    end

    subgraph BotModule [bot/ module]
        WH[Webhook Server]
        Adapters[Platform Adapters]
        Dispatcher[Command Dispatcher]
        Commands[Command Handlers]
    end

    subgraph Core [Core Modules]
        AS[AnalysisService]
        MA[MarketAnalyzer]
        NS[NotificationService]
    end

    FS -->|POST /bot/feishu| WH
    DT -->|POST /bot/dingtalk| WH
    WC -->|POST /bot/wecom| WH
    TG -->|POST /bot/telegram| WH

    WH --> Adapters
    Adapters -->|Unified message format| Dispatcher
    Dispatcher --> Commands
    Commands --> AS
    Commands --> MA
    Commands --> NS
```

---

## 2. Directory Structure

```
bot/
├── __init__.py             # Module entry, exports main classes
├── models.py               # Outbound response models (inbound model: src/domain/notification/bot_message.py)
├── dispatcher.py           # Command dispatcher (core)
├── handler.py              # Webhook handler functions (one per platform)
├── commands/               # Command handlers
│   ├── __init__.py
│   ├── base.py             # Abstract base class for commands
│   ├── analyze.py          # /analyze — stock analysis
│   ├── ask.py              # /ask — single-turn question
│   ├── batch.py            # /batch — batch watchlist analysis
│   ├── chat.py             # /chat — multi-turn strategy chat
│   ├── market.py           # /market — market review
│   ├── help.py             # /help — help text
│   └── status.py           # /status — system status
└── platforms/              # Platform adapters
    ├── __init__.py
    ├── base.py             # Abstract base class for platforms
    ├── dingtalk.py         # DingTalk bot
    ├── dingtalk_stream.py  # DingTalk Stream bot
    └── feishu_stream.py    # Feishu (Lark) Stream bot
```

---

## 3. Core Abstractions

### 3.1 Unified Message Model (inbound `src/domain/notification/bot_message.py` / outbound `bot/models.py`)

The inbound model `BotMessage` / `ChatType` / `Platform` is consumed by platform adapters, application orchestration (`src/application/analysis/pipeline.py`, `src/application/runtime/task_service.py`) and notification code (`src/application/notification/notification.py`). As a pure `dataclass`/`Enum` data contract it has been pushed down to the domain layer at `src/domain/notification/bot_message.py` (kept neutral: it depends on neither the `bot` driver layer nor the application layer). `bot/models.py` keeps only the outbound response models (`BotResponse` / `WebhookResponse`); `from bot import BotMessage, ChatType` still works.

```python
@dataclass
class BotMessage:
    platform: str       # Platform ID: feishu / dingtalk / wecom / telegram
    user_id: str        # Sender ID
    user_name: str      # Sender display name
    chat_id: str        # Conversation ID (group or DM)
    chat_type: str      # Conversation type: group / private
    content: str        # Message text
    raw_data: Dict      # Raw request data (platform-specific)
    timestamp: datetime
    mentioned: bool = False  # Whether the bot was @-mentioned

@dataclass
class BotResponse:
    text: str
    markdown: bool = False  # Whether the response is Markdown
    at_user: bool = True    # Whether to @-mention the sender
```

### 3.2 Platform Adapter Base (`bot/platforms/base.py`)

```python
class BotPlatform(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str: ...

    @abstractmethod
    def verify_request(self, headers: Dict, body: bytes) -> bool:
        """Verify request signature (security check)"""
        ...

    @abstractmethod
    def parse_message(self, data: Dict) -> Optional[BotMessage]:
        """Parse platform message into unified format"""
        ...

    @abstractmethod
    def format_response(self, response: BotResponse, message: BotMessage) -> WebhookResponse:
        """Convert unified response to platform format"""
        ...
```

### 3.3 Command Base Class (`bot/commands/base.py`)

```python
class BotCommand(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...          # e.g. 'analyze'

    @property
    @abstractmethod
    def aliases(self) -> List[str]: ... # e.g. ['a', 'analyse']

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def usage(self) -> str: ...

    @abstractmethod
    def execute(self, message: BotMessage, args: List[str]) -> BotResponse: ...
```

---

## 4. Supported Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/analyze` | Analyze a specific stock | `/analyze AAPL` or `/analyze 600519` |
| `/ask` | Single-turn question about a stock or the market | `/ask what is RSI for AAPL` |
| `/batch` | Batch-analyze your configured watchlist | `/batch` |
| `/chat` | Multi-turn strategy chat (maintains conversation context) | `/chat` |
| `/market` | Market review (A-shares / US stocks) | `/market` |
| `/help` | Show help text | `/help` |
| `/status` | Show system status | `/status` |

> **Stock code formats:** A-shares use 6-digit codes (e.g. `600519`); HK stocks prefix `hk` (e.g. `hk00700`); US stocks use ticker symbols (e.g. `AAPL`, `TSLA`).

---

## 5. `/status` and LLM configuration diagnostics

### Configuration precedence for readiness in `/status`

- The AI availability displayed by `/status` follows runtime precedence:
  - `LITELLM_CONFIG` (LiteLLM YAML)
  - `LLM_CHANNELS`
  - legacy provider keys (`GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`)
- If the primary model (`LITELLM_MODEL` or `AGENT_LITELLM_MODEL`) has no configured source in the active layer, `/status` shows `AI 服务未配置` and keeps the explicit reason line.
- Runtime dependency constraint in this repository is `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`; current status semantics are aligned with this constraint.
- This diagnostic follows the same readiness rules as `GET /api/v1/system/config/setup/status` for LLM checks: channels/yaml are active higher priority than legacy keys, and no silent migration is performed when toggling modes.

### Fallback and migration boundary

- When `LITELLM_CONFIG` or `LLM_CHANNELS` is active, lower-priority legacy provider keys are ignored as the active source for that run (no silent downgrade).
- This change only improves diagnosis and does not perform automatic migration: legacy configuration values are not deleted or rewritten during startup or status collection.

### Official compatibility references (for triage)

- LiteLLM docs: https://docs.litellm.ai/
- LiteLLM OpenAI-compatible provider: https://docs.litellm.ai/docs/providers/openai_compatible
- OpenAI Chat API: https://platform.openai.com/docs/api-reference/chat
- DeepSeek API docs: https://api-docs.deepseek.com/
- Kimi Moonshot compatibility: https://platform.moonshot.ai/docs/guide/compatibility
- Gemini OpenAI compatibility: https://ai.google.dev/gemini-api/docs/openai
- Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md

## 6. Webhook Routes

Handler functions for each platform live in `bot/handler.py`.
These routes are **not yet wired** into the FastAPI application — you must mount them manually.

| Route | Method | Status | Notes |
|-------|--------|--------|-------|
| `/bot/dingtalk` | POST | **Ready** | `DingtalkPlatform` is registered in `ALL_PLATFORMS` |
| `/bot/feishu` | POST | Stream only | Use `feishu_stream.py`; no Webhook adapter in `ALL_PLATFORMS` |
| `/bot/wecom` | POST | Not implemented | Handler exists but no platform adapter |
| `/bot/telegram` | POST | Not implemented | Handler exists but no platform adapter |

To mount the DingTalk webhook in your FastAPI app:

```python
from bot.handler import handle_dingtalk_webhook

@app.post("/bot/dingtalk")
async def dingtalk_webhook(request: Request):
    headers = dict(request.headers)
    body = await request.body()
    return handle_dingtalk_webhook(headers, body)
```

---

## 7. Configuration

Add the following to your `.env`. Some of these bot-specific keys are already listed in `.env.example` (for example the DingTalk and Feishu app credentials), while others are not, so treat this section as a consolidated reference for bot setup:

```dotenv
# --- Bot general ---
BOT_ENABLED=false
BOT_COMMAND_PREFIX=/

# --- Feishu (Lark) bot ---
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_VERIFICATION_TOKEN=    # Event verification token
FEISHU_ENCRYPT_KEY=           # Encryption key (optional)

# --- DingTalk bot ---
DINGTALK_APP_KEY=
DINGTALK_APP_SECRET=

# --- WeChat Work bot (in development) ---
WECOM_TOKEN=
WECOM_ENCODING_AES_KEY=

# --- Telegram bot ---
TELEGRAM_BOT_TOKEN=           # Get from @BotFather
TELEGRAM_WEBHOOK_SECRET=      # Webhook secret token
```

> Settings page: `BOT_ENABLED`, `BOT_COMMAND_PREFIX`, `BOT_ADMIN_USERS`, `FEISHU_VERIFICATION_TOKEN`, `FEISHU_ENCRYPT_KEY`, the Feishu delivery fields, and `EMAIL_SENDER_NAME` are now editable in the Web settings page under the Notification category. See [Environment variables](full-guide_EN.md#bot-and-event-callback-configuration) for the full field list.
>
> Effective boundary: `BOT_ENABLED` is read per request, so a saved change applies to the next callback. `BOT_COMMAND_PREFIX` and `BOT_ADMIN_USERS` are captured when the command dispatcher singleton is first built and the save path does not reset it, so they need a process restart. The Feishu event token and encrypt key are read when the Stream client connects, which also needs a restart.
>
> `BOT_ENABLED` only gates the webhook command entry; it does not drop established Feishu / DingTalk Stream connections, which are started by `FEISHU_STREAM_ENABLED` / `DINGTALK_STREAM_ENABLED` at startup.
>
> `BOT_ADMIN_USERS` has no visible effect yet: the dispatcher enforces `admin_only`, but no built-in command declares it (`bot/commands/batch.py` returns `False`).

---

## 7. Extending the Bot

### Adding a new platform adapter

1. Create a new file in `bot/platforms/`.
2. Subclass `BotPlatform` and implement `verify_request`, `parse_message`, `format_response`.
3. Mount the webhook route directly in your FastAPI app (for example in `api/app.py`) instead of `api/v1/router.py`, so the callback path stays `/bot/<platform>` rather than `/api/v1/bot/<platform>`.

### Adding a new command

1. Create a new file in `bot/commands/`.
2. Subclass `BotCommand` and implement the `execute` method.
3. Register the command in the dispatcher startup code.
