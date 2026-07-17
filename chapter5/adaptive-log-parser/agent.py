"""
agent.py —— 代码生成 Agent（自愈闭环的“大脑”）

职责：拿到无法解析的失败样本 + 报错，调用 OpenAI，生成一个能正确解析该格式的
Python 解析函数 `def parse(line: str) -> dict | None`。支持把上一轮自动测试的
失败报告作为反馈再次生成（迭代修复）。
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from openai import OpenAI

# .env 加载（可选依赖）
try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


SYSTEM_PROMPT = """你是一个"日志解析器代码生成器"。用户会给你一批**同一种未知格式**的日志样本，
以及现有系统解析失败的报错。你的任务：编写一个 Python 函数，把这种格式的每一行解析成结构化字段。

严格要求：
1. 只输出一个 Python 代码块（```python ... ```），不要任何解释文字。
2. 代码块里必须定义一个函数：def parse(line: str) -> dict | None
   - 输入是一行日志（字符串）。
   - 如果这行符合你要解析的格式，返回一个 dict，键为字段名（英文小写下划线），值为解析出的内容。
   - 如果这行**不符合**这种格式，必须返回 None（不要抛异常，把机会让给其它解析器）。
3. 只能使用 Python 标准库（re、json、datetime 等），不要 import 第三方库。
4. 不要有任何 print、input、文件读写、网络访问等副作用。
5. 必须解析出用户指定的**所有必需字段**（required_keys），字段值不能为空。
6. 尽量健壮：用正则/分隔符解析，容忍字段顺序内的空格。
"""


def _build_user_prompt(
    samples: List[str],
    required_keys: List[str],
    error_report: str,
    feedback: Optional[str],
) -> str:
    sample_block = "\n".join(samples)
    parts = [
        "现有系统无法解析下面这种格式的日志，请生成解析函数。",
        "",
        "【失败样本（同一种新格式）】",
        sample_block,
        "",
        f"【系统报错】\n{error_report}",
        "",
        f"【必需解析出的字段 required_keys】\n{required_keys}",
    ]
    if feedback:
        parts += [
            "",
            "【上一版代码没通过自动测试，请修复后重新生成】",
            feedback,
        ]
    return "\n".join(parts)


def _extract_code(text: str) -> str:
    """从模型回复中抽取 Python 代码块；没有围栏时退回整段文本。"""
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


class CodeGenAgent:
    def __init__(self, model: Optional[str] = None):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("未找到 OPENAI_API_KEY，请在环境变量或 .env 中设置。")
        base_url = os.getenv("OPENAI_BASE_URL")
        # timeout / max_retries：让偶发的网络/SSL 抖动自动重试，不至于整轮崩溃
        client_kwargs = {"api_key": api_key, "timeout": 60.0, "max_retries": 3}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = OpenAI(**client_kwargs)
        self.model = model or os.getenv("MODEL", "gpt-4o-mini")

    def generate_parser_code(
        self,
        samples: List[str],
        required_keys: List[str],
        error_report: str,
        feedback: Optional[str] = None,
    ) -> str:
        """调用 LLM 生成解析器代码，返回纯 Python 源码字符串。"""
        user_prompt = _build_user_prompt(samples, required_keys, error_report, feedback)
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        return _extract_code(resp.choices[0].message.content or "")
