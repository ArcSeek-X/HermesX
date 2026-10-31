

## 一、整体设计

```mermaid
flowchart TB
    subgraph Platforms [外部平台]
        FS[飞书]
        DT[钉钉]
        WC[企业微信（开发中）]
        TG[Telegram（开发中）]
        More[更多平台...]
    end

    subgraph BotModule [bot/ 模块]
        WH[Webhook Server]
        Adapters[平台适配器]
        Dispatcher[命令分发器]
        Commands[命令处理器]
    end

    subgraph Core [现有核心模块]
        AS[AnalysisService]
        MA[MarketAnalyzer]
        NS[NotificationService]
    end

    FS -->|POST /bot/feishu| WH
    DT -->|POST /bot/dingtalk| WH
    WC -->|POST /bot/wecom| WH
    TG -->|POST /bot/telegram| WH

    WH --> Adapters
    Adapters -->|统一消息格式| Dispatcher
    Dispatcher --> Commands
    Commands --> AS
    Commands --> MA
    Commands --> NS
```



## 二、目录结构

在项目根目录新建 `bot/` 目录：

```
bot/
├── __init__.py             # 模块入口，导出主要类
├── models.py               # 出站响应模型（入站消息模型见 src/domain/notification/bot_message.py）
├── dispatcher.py           # 命令分发器（核心）
├── commands/               # 命令处理器
│   ├── __init__.py
│   ├── base.py             # 命令抽象基类
│   ├── analyze.py          # /analyze 股票分析
│   ├── market.py           # /market 大盘复盘
│   ├── help.py             # /help 帮助信息
│   └── status.py           # /status 系统状态
└── platforms/              # 平台适配器
    ├── __init__.py
    ├── base.py             # 平台抽象基类
    ├── feishu.py           # 飞书机器人
    ├── dingtalk.py         # 钉钉机器人
    ├── dingtalk_stream.py  # 钉钉机器人Stream
    ├── wecom.py            # 企业微信机器人 （开发中）
    └── telegram.py         # Telegram 机器人 （开发中）
```

## 三、核心抽象设计

### 3.1 统一消息模型（入站 `src/domain/notification/bot_message.py` / 出站 `bot/models.py`）

入站消息模型 `BotMessage` / `ChatType` / `Platform` 被平台适配器、应用编排（`src/application/analysis/pipeline.py`、`src/application/runtime/task_service.py`）与通知实现（`src/application/notification/notification.py`）共同消费，作为纯 `dataclass`/`Enum` 数据契约已下沉到领域层 `src/domain/notification/bot_message.py`（保持中立、既不依赖 `bot` 驱动层也不依赖应用层）。`bot/models.py` 只保留驱动层返回的出站响应模型（`BotResponse` / `WebhookResponse`）；`from bot import BotMessage, ChatType` 仍可用。

```python
@dataclass
class BotMessage:
    """统一的机器人消息模型"""
    platform: str           # 平台标识: feishu/dingtalk/wecom/telegram
    user_id: str            # 发送者 ID
    user_name: str          # 发送者名称
    chat_id: str            # 会话 ID（群聊或私聊）
    chat_type: str          # 会话类型: group/private
    content: str            # 消息文本内容
    raw_data: Dict          # 原始请求数据（平台特定）
    timestamp: datetime     # 消息时间
    mentioned: bool = False # 是否@了机器人

@dataclass
class BotResponse:
    """统一的机器人响应模型"""
    text: str               # 回复文本
    markdown: bool = False  # 是否为 Markdown
    at_user: bool = True    # 是否@发送者
```

### 3.2 平台适配器基类 (`bot/platforms/base.py`)

```python
class BotPlatform(ABC):
    """平台适配器抽象基类"""
    
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台标识名称"""
        pass
    
    @abstractmethod
    def verify_request(self, headers: Dict, body: bytes) -> bool:
        """验证请求签名（安全校验）"""
        pass
    
    @abstractmethod
    def parse_message(self, data: Dict) -> Optional[BotMessage]:
        """解析平台消息为统一格式"""
        pass
    
    @abstractmethod
    def format_response(self, response: BotResponse) -> Dict:
        """将统一响应转换为平台格式"""
        pass
```

### 3.3 命令基类 (`bot/commands/base.py`)

```python
class BotCommand(ABC):
    """命令处理器抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """命令名称 (如 'analyze')"""
        pass
    
    @property
    @abstractmethod
    def aliases(self) -> List[str]:
        """命令别名 (如 ['a', '分析'])"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """命令描述"""
        pass
    
    @property
    @abstractmethod
    def usage(self) -> str:
        """使用说明"""
        pass
    
    @abstractmethod
    async def execute(self, message: BotMessage, args: List[str]) -> BotResponse:
        """执行命令"""
        pass
```

### 3.4 命令分发器 (`bot/dispatcher.py`)

```python
class CommandDispatcher:
    """命令分发器 - 单例模式"""
    
    def __init__(self):
        self._commands: Dict[str, BotCommand] = {}
        self._aliases: Dict[str, str] = {}
    
    def register(self, command: BotCommand) -> None:
        """注册命令"""
        self._commands[command.name] = command
        for alias in command.aliases:
            self._aliases[alias] = command.name
    
    def dispatch(self, message: BotMessage) -> BotResponse:
        """分发消息到对应命令"""
        # 1. 解析命令和参数
        # 2. 查找命令处理器
        # 3. 执行并返回响应
```

## 四、已支持的命令

| 命令 | 别名 | 说明 | 示例 |

|------|------|------|------|

| /analyze | /a, 分析 | 分析指定股票 | `/analyze 600519` |

| /market | /m, 大盘 | 大盘复盘 | `/market` |

| /batch | /b, 批量 | 批量分析自选股 | `/batch` |

| /help | /h, 帮助 | 显示帮助信息 | `/help` |

| /status | /s, 状态 | 系统状态 | `/status` |

## 五、`/status` 与模型配置诊断说明

### 可配置层级与可用性判断依据

- `/status` 显示的 LLM 可用性遵循系统统一运行时优先级：
  - `LITELLM_CONFIG`（LiteLLM YAML）
  - `LLM_CHANNELS`
  - legacy provider 键（`GEMINI_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`）
- 当主模型（`LITELLM_MODEL` 或 `AGENT_LITELLM_MODEL`）在当前激活层无可用来源时，会展示“AI 服务未配置”，并保留用户可见原因行。
- 本仓库 `requirements.txt` 的运行时依赖约束为 `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`，该约束内本链路以现有兼容行为为准。
- 该诊断规则与 `GET /api/v1/system/config/setup/status` 的 LLM 检查保持一致：`LITELLM_CONFIG`/`LLM_CHANNELS` 为高优先级；模式切换时不会做静默迁移，切回旧模式由用户显式恢复历史值或回滚。

### 回退与迁移边界

- `LITELLM_CONFIG` 与 `LLM_CHANNELS` 任一生效时，下层 legacy 配置会被该层忽略（不会继续作为本次调用来源）。
- 诊断增强不进行 silent migration：不会主动清空/删除 `GEMINI_*`、`OPENAI_*`、`ANTHROPIC_*`、`LITELLM_*` 的历史值，仅在可用性诊断上提示。

### 官方兼容来源（用于排障核对）

- LiteLLM 官网：<https://docs.litellm.ai/>
- LiteLLM OpenAI Compatible 说明：<https://docs.litellm.ai/docs/providers/openai_compatible>
- OpenAI Chat API：<https://platform.openai.com/docs/api-reference/chat>
- DeepSeek API 文档：<https://api-docs.deepseek.com/>
- Kimi Moonshot 兼容说明：<https://platform.moonshot.ai/docs/guide/compatibility>
- Gemini OpenAI 兼容说明：<https://ai.google.dev/gemini-api/docs/openai>
- Ollama API 文档：<https://github.com/ollama/ollama/blob/main/docs/api.md>

## 六、Webhook 路由

在 [api/v1/router.py](../api/v1/router.py) 中注册路由：

```python
# Webhook 路由
/bot/feishu      # POST - 飞书事件回调
/bot/dingtalk    # POST - 钉钉事件回调
/bot/wecom       # POST - 企业微信事件回调 （开发中）
/bot/telegram    # POST - Telegram 更新回调 （开发中）
```

## 配置

在 [settings.py](../src/config/settings.py) 中新增机器人配置：

```python
# === 机器人配置 ===
bot_enabled: bool = True               # 是否启用机器人（Webhook 命令入口）
bot_command_prefix: str = "/"          # 命令前缀

# 飞书机器人（事件订阅）
feishu_app_id: str                     # 已有
feishu_app_secret: str                 # 已有
feishu_verification_token: str         # 新增：事件校验 Token
feishu_encrypt_key: str                # 新增：加密密钥

# 钉钉机器人（应用）
dingtalk_app_key: str                  # 新增
dingtalk_app_secret: str               # 新增

# 企业微信机器人（开发中）
wecom_token: str                       # 新增：回调 Token
wecom_encoding_aes_key: str            # 新增：EncodingAESKey

# Telegram 机器人（开发中）
telegram_bot_token: str                # 已有
telegram_webhook_secret: str           # 新增：Webhook 密钥
```

> 设置页入口：`BOT_ENABLED` / `BOT_COMMAND_PREFIX` / `BOT_ADMIN_USERS` / `FEISHU_VERIFICATION_TOKEN` / `FEISHU_ENCRYPT_KEY` 以及飞书发送形态与 `EMAIL_SENDER_NAME` 已在 Web 设置页「通知」分类开放，完整字段说明见[环境变量完整列表](full-guide.md#机器人与事件回调配置)。
>
> 生效边界：`BOT_ENABLED` 按请求读取（通过 `Config` 单例），保存后下一次回调即生效；`BOT_COMMAND_PREFIX` 与 `BOT_ADMIN_USERS` 在命令分发器单例首次构建时读取，且保存链路不会重置分发器，因此需重启进程；飞书事件 Token / 密钥在 Stream 客户端建连时读取，同样需重启。
>
> `BOT_ENABLED` 只控制 Webhook 命令入口，不断开已启动的飞书 / 钉钉 Stream 长连接；长连接由 `FEISHU_STREAM_ENABLED` / `DINGTALK_STREAM_ENABLED` 在启动时决定。

## 扩展说明
### 怎样新增一个通知平台

1. 在 `bot/platforms/` 创建新文件
2. 继承 `BotPlatform` 基类
3. 实现 `verify_request`, `parse_message`, `format_response`
4. 在路由中注册 Webhook 端点

### 怎样新增新增命令

1. 在 `bot/commands/` 创建新文件
2. 继承 `BotCommand` 基类
3. 实现 `execute` 方法
4. 在分发器中注册命令

## 安全相关配置

- 支持命令频率限制（防刷）
- 敏感操作（如批量分析）可设置权限白名单

在 [settings.py](../src/config/settings.py) 中新增机器人安全配置：

```python
    bot_rate_limit_requests: int = 10     # 频率限制：窗口内最大请求数
    bot_rate_limit_window: int = 60       # 频率限制：窗口时间（秒）
    bot_admin_users: List[str] = field(default_factory=list)  # 管理员用户 ID 列表，限制敏感操作
```

> 当前状态：分发器已实现 `admin_only` 校验，但内置命令均未声明 `admin_only`（`bot/commands/batch.py` 返回 `False`），因此 `BOT_ADMIN_USERS` 现在不会拦住任何命令，也不会放开任何新能力。它是为后续敏感命令预留的名单，一旦有命令返回 `True`，未列入的用户会被拒绝。
>
> `BOT_RATE_LIMIT_REQUESTS` / `BOT_RATE_LIMIT_WINDOW` 属于内部防刷参数，与 `DISCORD_MAX_WORDS` 一起列在 `WEB_SETTINGS_HIDDEN_FROM_UI`，只在部署侧通过 `.env` 调整。
