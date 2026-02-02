import json
import logging
from datetime import datetime
from pathlib import Path


BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 配置主日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

# 创建专门的提示词日志记录器
prompt_logger = logging.getLogger("prompt")
prompt_handler = logging.FileHandler(LOG_DIR / "prompts.log", encoding="utf-8")
prompt_handler.setFormatter(logging.Formatter("%(asctime)s\n%(message)s\n" + "="*80))
prompt_logger.addHandler(prompt_handler)
prompt_logger.setLevel(logging.INFO)
prompt_logger.propagate = False  # 不传播到根 logger


def log_event(event_type: str, data: dict) -> None:
    """记录结构化事件日志"""
    log_entry = {"timestamp": datetime.now().isoformat(), "event": event_type, "data": data}
    logging.info(json.dumps(log_entry, ensure_ascii=False))


def log_prompt(session_id: str, question: str, prompt: str, messages: list, metadata: dict) -> None:
    """
    记录完整的提示词注入日志
    
    Args:
        session_id: 会话 ID
        question: 用户问题
        prompt: 构建的 system prompt
        messages: 完整的消息列表
        metadata: 元数据（skills、token 估算等）
    """
    log_content = f"""
{'='*80}
SESSION: {session_id}
TIMESTAMP: {datetime.now().isoformat()}
{'='*80}

[USER QUESTION]
{question}

{'='*80}
[METADATA]
{'='*80}
Skills Involved: {', '.join(metadata.get('skills', []))}
Newly Loaded: {', '.join(metadata.get('newly_loaded', [])) if metadata.get('newly_loaded') else 'None (reusing loaded)'}
Prompt Length: {len(prompt)} chars
Estimated Tokens: ~{len(prompt) // 4}
History Messages: {len(metadata.get('history', []))}

{'='*80}
[SYSTEM PROMPT]
{'='*80}
{prompt}

{'='*80}
[FULL MESSAGES SENT TO AI]
{'='*80}
{json.dumps(messages, ensure_ascii=False, indent=2)}

{'='*80}
"""
    prompt_logger.info(log_content)
