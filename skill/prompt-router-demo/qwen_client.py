import json
import os
import urllib.request


DEFAULT_QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DEFAULT_QWEN_MODEL = "qwen3-coder-plus"


class QwenClient:
    def __init__(self) -> None:
        self.api_key = os.environ.get("DASHSCOPE_API_KEY", "sk-597b7807a9b94b818b4f806ad42a8562").strip()
        self.base_url = os.environ.get("QWEN_BASE_URL", DEFAULT_QWEN_BASE_URL).strip()
        self.model = os.environ.get("QWEN_MODEL", DEFAULT_QWEN_MODEL).strip()
        if not self.api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required.")

    def chat(self, messages: list[dict], temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError(f"Unexpected response: {data}")
        message = choices[0].get("message", {})
        return message.get("content", "").strip()







