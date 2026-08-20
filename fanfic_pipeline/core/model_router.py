"""
Multi-Model & Multi-Provider Routing Engine (v0.8 Production-Ready):
- Native support for CLIProxyAPI (http://127.0.0.1:8317/v1, step-3.7-flash, glm-5.2)
- OpenRouter, DeepSeek, Anthropic, OpenAI, Local LM Studio & Ollama
- Built-in Exponential Backoff Retry (3 attempts) for HTTP 429 & 5xx errors
- Fixed typos and dynamic configuration override
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class AgentModelConfig(BaseModel):
    provider: str = Field(default="cliproxyapi", description="cliproxyapi, openrouter, deepseek, anthropic, openai, local_lmstudio, local_ollama")
    model_name: str
    base_url: Optional[str] = None
    api_key_env: Optional[str] = "CLIPROXY_KEY"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout_seconds: int = 90
    max_retries: int = 3

class PipelineModelRouter(BaseModel):
    architect_agent: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(
            provider="cliproxyapi",
            model_name="step-3.7-flash",
            base_url=os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
            api_key_env="CLIPROXY_KEY",
            temperature=0.6,
            max_tokens=4096
        )
    )
    composer_agent: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(
            provider="cliproxyapi",
            model_name="step-3.7-flash",
            base_url=os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
            api_key_env="CLIPROXY_KEY",
            temperature=0.7,
            max_tokens=4096
        )
    )
    writer_agent: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(
            provider="cliproxyapi",
            model_name="step-3.7-flash",
            base_url=os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
            api_key_env="CLIPROXY_KEY",
            temperature=0.85,
            max_tokens=6000
        )
    )
    ooc_critic_agent: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(
            provider="cliproxyapi",
            model_name="glm-5.2",
            base_url=os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
            api_key_env="CLIPROXY_KEY",
            temperature=0.3,
            max_tokens=4096
        )
    )
    polisher_agent: AgentModelConfig = Field(
        default_factory=lambda: AgentModelConfig(
            provider="cliproxyapi",
            model_name="glm-5.2",
            base_url=os.environ.get("CLIPROXY_BASE_URL", "http://127.0.0.1:8317/v1"),
            api_key_env="CLIPROXY_KEY",
            temperature=0.5,
            max_tokens=4096
        )
    )

    def save_to_file(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_from_file(cls, path: str) -> "PipelineModelRouter":
        if not os.path.exists(path):
            router = cls()
            router.save_to_file(path)
            return router
        with open(path, "r", encoding="utf-8") as f:
            return cls(**json.load(f))

class LLMInvoker:
    """Universal HTTP client with Exponential Backoff Retry."""
    def __init__(self, router: Optional[PipelineModelRouter] = None):
        self.router = router or PipelineModelRouter()

    @classmethod
    def call_agent_llm(cls, config_or_invoker: Any, system_or_agent: Any, user_or_sys: str = "", json_mode: bool = False) -> str:
        if isinstance(config_or_invoker, cls):
            # instance call: invoker.call_agent_llm("architect_agent", user_prompt, system_prompt, json_mode)
            agent_name = str(system_or_agent)
            config = getattr(config_or_invoker.router, agent_name, config_or_invoker.router.architect_agent)
            user_prompt = user_or_sys
            system_prompt = "You are a helpful AI assistant."
            return cls._call(config, system_prompt, user_prompt, json_mode)
        elif isinstance(config_or_invoker, AgentModelConfig):
            # static call: LLMInvoker.call_agent_llm(config, system_prompt, user_prompt, json_mode)
            config = config_or_invoker
            system_prompt = system_or_agent
            user_prompt = user_or_sys
            return cls._call(config, system_prompt, user_prompt, json_mode)
        else:
            return ""


    @classmethod
    def _call(cls, config: AgentModelConfig, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        # Determine API key: check env var first; if not set or looks like literal key, use directly
        api_key = os.environ.get(config.api_key_env or "", "")
        if not api_key and config.api_key_env:
            if config.api_key_env.startswith("cpa-") or config.api_key_env.startswith("sk-") or len(config.api_key_env) > 15:
                api_key = config.api_key_env

        raw_url = config.base_url or os.environ.get("CLIPROXY_BASE_URL", "http://47.237.140.200/v1")
        base_url = raw_url.removesuffix("/chat/completions").rstrip("/")
        if not base_url.endswith("/v1") and "/v1" not in base_url:
            base_url = f"{base_url}/v1"

        endpoint = f"{base_url}/chat/completions"


        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'cpa-local-9f3a7e2b1c4d'}"
        }
        if "openrouter" in base_url:
            headers["HTTP-Referer"] = "https://github.com/Narcooo/inkos"
            headers["X-Title"] = "Fanfic AI Studio"

        payload = {
            "model": config.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        last_err = None
        for attempt in range(1, config.max_retries + 1):
            try:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(endpoint, data=req_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    return result["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:
                err_msg = e.read().decode("utf-8", errors="ignore")
                last_err = RuntimeError(f"HTTP error {e.code} from {config.provider} ({config.model_name}): {err_msg}")
                if e.code in [429, 500, 502, 503, 504] and attempt < config.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err
            except Exception as e:
                last_err = RuntimeError(f"Network error from {config.provider} ({config.model_name}): {str(e)}")
                if attempt < config.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err

        raise last_err or RuntimeError("Max retries exceeded without response.")

