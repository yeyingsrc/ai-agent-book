"""
统一的 LLM 客户端配置。

默认使用 OpenAI（读取 OPENAI_API_KEY，模型 gpt-4o-mini）。
也支持通过环境变量 LLM_PROVIDER 切换到 Moonshot / 火山方舟(ARK)，
它们都兼容 OpenAI 的 Chat Completions + 工具调用接口。

    export LLM_PROVIDER=openai   # 默认
    export LLM_PROVIDER=moonshot # 用 MOONSHOT_API_KEY
    export LLM_PROVIDER=ark      # 用 ARK_API_KEY，并需设置 ARK_MODEL
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 各提供商的默认配置：base_url / 环境变量名 / 默认模型
_PROVIDERS = {
    "openai": {
        "base_url": None,  # 使用 SDK 默认
        "key_env": "OPENAI_API_KEY",
        "default_model": "gpt-4o-mini",
    },
    "moonshot": {
        "base_url": "https://api.moonshot.cn/v1",
        "key_env": "MOONSHOT_API_KEY",
        "default_model": "kimi-k2-0905-preview",
    },
    "ark": {
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "key_env": "ARK_API_KEY",
        # ARK 需要用推理接入点(endpoint id) 作为 model，请通过 ARK_MODEL 指定
        "default_model": os.getenv("ARK_MODEL", "doubao-seed-1-6-250615"),
    },
}


def get_provider() -> str:
    return os.getenv("LLM_PROVIDER", "openai").lower().strip()


def get_model() -> str:
    """允许用 LLM_MODEL 覆盖默认模型。"""
    override = os.getenv("LLM_MODEL")
    if override:
        return override
    provider = get_provider()
    if provider not in _PROVIDERS:
        raise ValueError(f"未知的 LLM_PROVIDER: {provider}")
    return _PROVIDERS[provider]["default_model"]


def get_client() -> OpenAI:
    provider = get_provider()
    if provider not in _PROVIDERS:
        raise ValueError(f"未知的 LLM_PROVIDER: {provider}")
    cfg = _PROVIDERS[provider]
    api_key = os.getenv(cfg["key_env"])
    if not api_key:
        raise RuntimeError(
            f"环境变量 {cfg['key_env']} 未设置。请参考 env.example 配置后重试。"
        )
    kwargs = {"api_key": api_key}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


# 全部 LLM 调用统一使用低温度，保证结果可复现
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
